from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.domain.exceptions import DocumentProcessingError
from app.domain.interfaces import DocumentRepository, EmbeddingProvider, IngestionJobRepository, VectorStoreRepository
from app.domain.models import Document, DocumentChunk, IngestionJob, IngestionStatus, utcnow


@dataclass(slots=True)
class QaCsvImportResult:
    document: Document
    job: IngestionJob
    imported_chunks: int
    skipped_rows: int


class QaCsvImportService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        job_repository: IngestionJobRepository,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreRepository,
    ) -> None:
        self._document_repository = document_repository
        self._job_repository = job_repository
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def import_csv(
        self,
        csv_path: Path,
        question_column: str = "question",
        answer_column: str = "answer",
        document_name: str | None = None,
    ) -> QaCsvImportResult:
        path = csv_path.expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise DocumentProcessingError(f"CSV file '{path}' was not found.")
        if path.suffix.lower() != ".csv":
            raise DocumentProcessingError("The importer expects a .csv file.")

        document = Document(
            id=str(uuid4()),
            filename=document_name or path.name,
            content_type="text/csv",
            extension=".csv",
            size_bytes=path.stat().st_size,
            storage_path=str(path),
            status=IngestionStatus.PROCESSING,
        )
        job = IngestionJob(
            id=str(uuid4()),
            document_id=document.id,
            status=IngestionStatus.PROCESSING,
        )
        await self._document_repository.save(document)
        await self._job_repository.save(job)

        try:
            chunks, skipped_rows = await asyncio.to_thread(
                self._build_chunks,
                path,
                document.id,
                document.filename,
                question_column,
                answer_column,
            )
            if not chunks:
                raise DocumentProcessingError("No valid question/answer rows were found in the CSV file.")

            await self._vector_store.ensure_collection()
            vectors = await self._embedding_provider.embed_documents([chunk.content for chunk in chunks])
            await self._vector_store.upsert(chunks=chunks, vectors=vectors)

            document.status = IngestionStatus.COMPLETED
            document.error = None
            job.status = IngestionStatus.COMPLETED
            job.error = None
            job.processed_chunks = len(chunks)
        except Exception as exc:
            document.status = IngestionStatus.FAILED
            document.error = str(exc)
            job.status = IngestionStatus.FAILED
            job.error = str(exc)
            job.processed_chunks = 0
            raise
        finally:
            timestamp = utcnow()
            document.updated_at = timestamp
            job.updated_at = timestamp
            await self._document_repository.save(document)
            await self._job_repository.save(job)

        return QaCsvImportResult(
            document=document,
            job=job,
            imported_chunks=len(chunks),
            skipped_rows=skipped_rows,
        )

    def _build_chunks(
        self,
        csv_path: Path,
        document_id: str,
        filename: str,
        question_column: str,
        answer_column: str,
    ) -> tuple[list[DocumentChunk], int]:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(2048)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(handle, dialect=dialect)
            if not reader.fieldnames:
                raise DocumentProcessingError("CSV file must include a header row.")

            normalized_headers = {header.strip().lower(): header for header in reader.fieldnames if header}
            question_header = normalized_headers.get(question_column.strip().lower())
            answer_header = normalized_headers.get(answer_column.strip().lower())
            if question_header is None or answer_header is None:
                available_columns = ", ".join(reader.fieldnames)
                raise DocumentProcessingError(
                    "CSV file is missing the required question/answer columns. "
                    f"Expected '{question_column}' and '{answer_column}'. Available columns: {available_columns}"
                )

            chunks: list[DocumentChunk] = []
            skipped_rows = 0
            for row_number, row in enumerate(reader, start=1):
                question = (row.get(question_header) or "").strip()
                answer = (row.get(answer_header) or "").strip()
                if not question or not answer:
                    skipped_rows += 1
                    continue

                chunks.append(
                    DocumentChunk(
                        id=str(uuid4()),
                        document_id=document_id,
                        filename=filename,
                        content=f"Question: {question}\nAnswer: {answer}",
                        chunk_index=len(chunks),
                        metadata={
                            "source_type": "qa_csv",
                            "row_number": row_number,
                            "question_column": question_header,
                            "answer_column": answer_header,
                            "question": question,
                            "answer": answer,
                        },
                    )
                )

        return chunks, skipped_rows
