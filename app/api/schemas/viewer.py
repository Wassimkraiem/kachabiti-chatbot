from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import IngestionStatus


class ViewerDocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    extension: str
    size_bytes: int
    status: IngestionStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class ViewerChunkResponse(BaseModel):
    id: str
    document_id: str
    filename: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ViewerOverviewResponse(BaseModel):
    collection_name: str
    documents: list[ViewerDocumentResponse]
    chunks: list[ViewerChunkResponse]
    total_documents: int
    total_chunks: int
    page_size: int
    next_offset: str | None = None
    collection_exists: bool
    qdrant_available: bool
    qdrant_error: str | None = None


class QdrantDocumentResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: IngestionStatus | None = None
    content_type: str | None = None
    extension: str | None = None
    size_bytes: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    error: str | None = None


class QdrantDocumentsResponse(BaseModel):
    collection_name: str
    documents: list[QdrantDocumentResponse]
    total_documents: int
    total_chunks: int
    collection_exists: bool
    qdrant_available: bool
    qdrant_error: str | None = None
