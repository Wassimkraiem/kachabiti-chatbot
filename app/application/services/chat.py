from __future__ import annotations

from app.domain.interfaces import ChatModelProvider
from app.domain.models import ChatMessage, ChatResult
from app.application.services.retrieval import RetrievalService


class RagChatService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        chat_provider: ChatModelProvider,
        default_top_k: int,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._chat_provider = chat_provider
        self._default_top_k = default_top_k

    async def complete(
        self,
        message: str,
        history: list[ChatMessage],
        top_k: int | None = None,
    ) -> ChatResult:
        retrieval_limit = top_k or self._default_top_k
        sources = await self._retrieval_service.retrieve(query=message, limit=retrieval_limit)
        if not sources:
            return ChatResult(
                answer="I do not have enough indexed context to answer that question yet.",
                sources=[],
                model=self._chat_provider.model_name,
            )

        answer = await self._chat_provider.generate_answer(
            question=message,
            history=history,
            contexts=sources,
        )
        return ChatResult(answer=answer, sources=sources, model=self._chat_provider.model_name)
