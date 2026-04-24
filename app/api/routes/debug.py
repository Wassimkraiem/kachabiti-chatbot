from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas.debug import PromptDebugResponse, PromptMessageResponse
from app.core.settings import get_settings
from app.infrastructure.ai.langsmith_integration import (
    configure_langsmith_environment,
    describe_prompt_messages,
    load_chat_prompt,
)

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


@router.get(
    "/prompt",
    response_model=PromptDebugResponse,
    summary="Inspect the currently resolved chat prompt",
)
async def get_current_prompt() -> PromptDebugResponse:
    settings = get_settings()
    configure_langsmith_environment(settings)
    prompt, source = load_chat_prompt(
        prompt_name=settings.langsmith_prompt_name,
        prompt_tag=settings.langsmith_prompt_tag,
    )
    return PromptDebugResponse(
        source=source,
        input_variables=sorted(getattr(prompt, "input_variables", [])),
        messages=[
            PromptMessageResponse(role=item["role"], content=item["content"])
            for item in describe_prompt_messages(prompt)
        ],
    )
