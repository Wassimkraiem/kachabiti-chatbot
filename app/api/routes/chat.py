from fastapi import APIRouter, Depends

from app.api.dependencies import get_service_container
from app.api.schemas.chat import ChatCompletionRequest, ChatCompletionResponse, SourceChunkResponse
from app.core.container import ServiceContainer
from app.domain.models import ChatMessage

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    summary="Run a grounded chat completion",
)
@router.post(
    "/chat",
    response_model=ChatCompletionResponse,
    summary="Run a grounded chat completion",
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    container: ServiceContainer = Depends(get_service_container),
) -> ChatCompletionResponse:
    result = await container.chat_service.complete(
        message=request.message,
        history=[ChatMessage(role=item.role, content=item.content) for item in request.history],
        top_k=request.top_k,
    )
    return ChatCompletionResponse(
        answer=result.answer,
        model=result.model,
        sources=[
            SourceChunkResponse(
                id=item.id,
                document_id=item.document_id,
                filename=item.filename,
                content=item.content,
                score=item.score,
                metadata=item.metadata,
            )
            for item in result.sources
        ],
    )
