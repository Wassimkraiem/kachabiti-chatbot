from pathlib import Path

import pytest

from app.application.services.qa_csv_import import QaCsvImportService
from app.domain.exceptions import DocumentProcessingError
from app.domain.models import Document, DocumentChunk, IngestionJob
from app.infrastructure.repositories.file_metadata import JsonDocumentRepository, JsonIngestionJobRepository


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def is_configured(self) -> bool:
        return True


class FakeVectorStore:
    def __init__(self) -> None:
        self.collection_created = False
        self.saved_chunks: list[DocumentChunk] = []
        self.saved_vectors: list[list[float]] = []

    async def ensure_collection(self) -> None:
        self.collection_created = True

    async def upsert(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> None:
        self.saved_chunks = chunks
        self.saved_vectors = vectors

    async def search(self, query_vector: list[float], limit: int):
        raise NotImplementedError

    async def ping(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_import_csv_writes_question_answer_chunks(tmp_path: Path):
    csv_path = tmp_path / "faq.csv"
    csv_path.write_text("question,answer\nWhat is Kachabiti?,A chatbot.\nHow to use it?,Upload a file.\n", "utf-8")

    vector_store = FakeVectorStore()
    service = QaCsvImportService(
        document_repository=JsonDocumentRepository(tmp_path / "documents"),
        job_repository=JsonIngestionJobRepository(tmp_path / "jobs"),
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=vector_store,
    )

    result = await service.import_csv(csv_path)

    assert result.imported_chunks == 2
    assert result.skipped_rows == 0
    assert result.document.status == "completed"
    assert result.job.processed_chunks == 2
    assert vector_store.collection_created is True
    assert vector_store.saved_chunks[0].content == "Question: What is Kachabiti?\nAnswer: A chatbot."
    assert vector_store.saved_chunks[0].metadata["source_type"] == "qa_csv"


@pytest.mark.asyncio
async def test_import_csv_skips_rows_with_missing_values(tmp_path: Path):
    csv_path = tmp_path / "faq.csv"
    csv_path.write_text("question,answer\nWhat is Kachabiti?,A chatbot.\nMissing answer,\n,Missing question\n", "utf-8")

    service = QaCsvImportService(
        document_repository=JsonDocumentRepository(tmp_path / "documents"),
        job_repository=JsonIngestionJobRepository(tmp_path / "jobs"),
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore(),
    )

    result = await service.import_csv(csv_path)

    assert result.imported_chunks == 1
    assert result.skipped_rows == 2


@pytest.mark.asyncio
async def test_import_csv_requires_question_and_answer_headers(tmp_path: Path):
    csv_path = tmp_path / "faq.csv"
    csv_path.write_text("prompt,response\nWhat is Kachabiti?,A chatbot.\n", "utf-8")

    service = QaCsvImportService(
        document_repository=JsonDocumentRepository(tmp_path / "documents"),
        job_repository=JsonIngestionJobRepository(tmp_path / "jobs"),
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore(),
    )

    with pytest.raises(DocumentProcessingError):
        await service.import_csv(csv_path)
