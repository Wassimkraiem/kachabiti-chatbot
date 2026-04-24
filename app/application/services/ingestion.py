from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from app.domain.exceptions import DocumentProcessingError, UnsupportedFileTypeError
from app.domain.interfaces import (
    DocumentRepository,
    EmbeddingProvider,
    FileStore,
    IngestionJobRepository,
    VectorStoreRepository,
)
from app.domain.models import Document, IngestionJob, IngestionStatus, utcnow
from app.infrastructure.parsers.chunker import TextChunker
from app.infrastructure.parsers.registry import ParserRegistry

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        job_repository: IngestionJobRepository,
        file_store: FileStore,
        allowed_extensions: set[str],
        max_upload_size_bytes: int,
    ) -> None:
        self._document_repository = document_repository
        self._job_repository = job_repository
        self._file_store = file_store
        self._allowed_extensions = allowed_extensions
        self._max_upload_size_bytes = max_upload_size_bytes

    async def create_ingestion(
        self,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> tuple[Document, IngestionJob]:
        extension = Path(filename).suffix.lower()
        if extension not in self._allowed_extensions:
            raise UnsupportedFileTypeError(f"Unsupported file type '{extension}'.")
        if not content:
            raise DocumentProcessingError("Uploaded file is empty.")
        if len(content) > self._max_upload_size_bytes:
            raise DocumentProcessingError("Uploaded file exceeds the configured size limit.")

        document_id = str(uuid4())
        job_id = str(uuid4())
        storage_path = await self._file_store.save(document_id=document_id, filename=filename, content=content)

        document = Document(
            id=document_id,
            filename=filename,
            content_type=content_type,
            extension=extension,
            size_bytes=len(content),
            storage_path=str(storage_path),
        )
        job = IngestionJob(id=job_id, document_id=document_id)

        await self._document_repository.save(document)
        await self._job_repository.save(job)
        logger.info("Created ingestion job", extra={"document_id": document_id, "job_id": job_id})
        return document, job

    async def get_document(self, document_id: str) -> Document:
        return await self._document_repository.get(document_id)

    async def get_job(self, job_id: str) -> IngestionJob:
        return await self._job_repository.get(job_id)


class DocumentProcessingService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        job_repository: IngestionJobRepository,
        parser_registry: ParserRegistry,
        chunker: TextChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreRepository,
    ) -> None:
        self._document_repository = document_repository
        self._job_repository = job_repository
        self._parser_registry = parser_registry
        self._chunker = chunker
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def process(self, document_id: str, job_id: str) -> None:
        document = await self._document_repository.get(document_id)
        job = await self._job_repository.get(job_id)
        document.status = IngestionStatus.PROCESSING
        job.status = IngestionStatus.PROCESSING
        await self._document_repository.save(document)
        await self._job_repository.save(job)

        try:
            parser = self._parser_registry.get_parser(document.storage_path)
            sections = await parser.parse(Path(document.storage_path))
            chunks = self._chunker.chunk(
                document_id=document.id,
                filename=document.filename,
                sections=sections,
            )
            if not chunks:
                raise DocumentProcessingError("No text could be extracted from the uploaded file.")

            await self._vector_store.ensure_collection()
            vectors = await self._embedding_provider.embed_documents([chunk.content for chunk in chunks])
            await self._vector_store.upsert(chunks=chunks, vectors=vectors)

            document.status = IngestionStatus.COMPLETED
            document.error = None
            job.status = IngestionStatus.COMPLETED
            job.error = None
            job.processed_chunks = len(chunks)
        except Exception as exc:
            logger.exception("Document processing failed", extra={"document_id": document_id, "job_id": job_id})
            document.status = IngestionStatus.FAILED
            document.error = str(exc)
            job.status = IngestionStatus.FAILED
            job.error = str(exc)
        finally:
            timestamp = utcnow()
            document.updated_at = timestamp
            job.updated_at = timestamp
            await self._document_repository.save(document)
            await self._job_repository.save(job)
