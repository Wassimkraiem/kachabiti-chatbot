from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QdrantQuestionWriteRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=12000)


class QdrantQuestionResponse(BaseModel):
    id: str
    question: str
    answer: str
    document_id: str
    filename: str
    chunk_index: int
    source_type: str | None = None
    updated_at: datetime | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QdrantQuestionsResponse(BaseModel):
    collection_name: str
    questions: list[QdrantQuestionResponse]
    total_questions: int
    collection_exists: bool
    qdrant_available: bool
    qdrant_error: str | None = None
