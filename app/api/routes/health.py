from fastapi import APIRouter, Depends

from app.api.dependencies import get_service_container
from app.core.container import ServiceContainer

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def readiness(
    container: ServiceContainer = Depends(get_service_container),
) -> dict[str, bool | str]:
    qdrant_ready = await container.vector_store.ping()
    openai_ready = await container.embedding_provider.is_configured() and await container.chat_provider.is_configured()
    ready = qdrant_ready and openai_ready
    return {
        "status": "ready" if ready else "degraded",
        "qdrant": qdrant_ready,
        "openai": openai_ready,
    }

