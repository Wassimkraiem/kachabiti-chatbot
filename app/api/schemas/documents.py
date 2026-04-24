from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models import IngestionStatus


class IngestDocumentResponse(BaseModel):
    document_id: str
    job_id: str
    status: IngestionStatus


class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    extension: str
    size_bytes: int
    status: IngestionStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class IngestionJobResponse(BaseModel):
    id: str
    document_id: str
    status: IngestionStatus
    created_at: datetime
    updated_at: datetime
    processed_chunks: int = Field(default=0)
    error: str | None = None

