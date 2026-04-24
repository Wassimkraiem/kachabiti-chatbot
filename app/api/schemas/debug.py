from pydantic import BaseModel, Field


class PromptMessageResponse(BaseModel):
    role: str
    content: str


class PromptDebugResponse(BaseModel):
    source: str
    input_variables: list[str] = Field(default_factory=list)
    messages: list[PromptMessageResponse] = Field(default_factory=list)
