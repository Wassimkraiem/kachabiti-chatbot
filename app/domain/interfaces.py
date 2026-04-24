from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.models import (
    ChatMessage,
    Document,
    DocumentChunk,
    IngestionJob,
    ParsedSection,
    RetrievedChunk,
)


class DocumentRepository(Protocol):
    async def save(self, document: Document) -> Document: ...

    async def get(self, document_id: str) -> Document: ...


class IngestionJobRepository(Protocol):
    async def save(self, job: IngestionJob) -> IngestionJob: ...

    async def get(self, job_id: str) -> IngestionJob: ...


class FileStore(Protocol):
    async def save(self, document_id: str, filename: str, content: bytes) -> Path: ...


class DocumentParser(Protocol):
    supported_extensions: set[str]

    async def parse(self, path: Path) -> list[ParsedSection]: ...


class EmbeddingProvider(Protocol):
    model_name: str

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...

    async def is_configured(self) -> bool: ...


class ChatModelProvider(Protocol):
    model_name: str

    async def generate_answer(
        self,
        question: str,
        history: list[ChatMessage],
        contexts: list[RetrievedChunk],
    ) -> str: ...

    async def is_configured(self) -> bool: ...


class VectorStoreRepository(Protocol):
    async def ensure_collection(self) -> None: ...

    async def upsert(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> None: ...

    async def search(self, query_vector: list[float], limit: int) -> list[RetrievedChunk]: ...

    async def ping(self) -> bool: ...
