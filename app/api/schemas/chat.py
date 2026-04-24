from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessageRequest] = Field(default_factory=list)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceChunkResponse(BaseModel):
    id: str
    document_id: str
    filename: str
    content: str
    score: float
    metadata: dict[str, object] = Field(default_factory=dict)


class ChatCompletionResponse(BaseModel):
    answer: str
    model: str
    sources: list[SourceChunkResponse] = Field(default_factory=list)

