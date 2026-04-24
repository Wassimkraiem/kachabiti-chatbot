from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.domain.exceptions import ConfigurationError
from app.domain.models import ChatMessage, RetrievedChunk
from app.infrastructure.ai.langsmith_integration import (
    build_context_text,
    inject_history,
    load_chat_prompt,
    to_langchain_history,
)


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str, model_name: str, base_url: str | None = None) -> None:
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY is not configured.")

        self.model_name = model_name
        self._client = OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(text)

    async def is_configured(self) -> bool:
        return True


class OpenAIChatProvider:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        prompt_name: str | None = None,
        prompt_tag: str = "latest",
    ) -> None:
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY is not configured.")

        self.model_name = model_name
        self._model = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,
        )
        self._prompt_name = prompt_name
        self._prompt_tag = prompt_tag

    async def generate_answer(
        self,
        question: str,
        history: list[ChatMessage],
        contexts: list[RetrievedChunk],
    ) -> str:
        prompt, prompt_source = load_chat_prompt(prompt_name=self._prompt_name, prompt_tag=self._prompt_tag)
        prompt_value = await prompt.ainvoke(
            {
                "question": question,
                "context": build_context_text(contexts),
            },
            config={
                "run_name": "KachabitiChatPrompt",
                "tags": ["kachabiti", "prompt"],
                "metadata": {
                    "prompt_source": prompt_source,
                    "context_chunk_count": len(contexts),
                },
            },
        )
        prompt_messages = prompt_value.to_messages()
        history_messages = to_langchain_history(history)
        response = await self._model.ainvoke(
            inject_history(prompt_messages, history_messages),
            config={
                "run_name": "KachabitiChatModel",
                "tags": ["kachabiti", "chat"],
                "metadata": {
                    "prompt_source": prompt_source,
                    "context_chunk_count": len(contexts),
                },
            },
        )
        return self._stringify_content(response.content)

    async def is_configured(self) -> bool:
        return True

    @staticmethod
    def _stringify_content(content: str | list[str | dict[str, object]]) -> str:
        if isinstance(content, str):
            return content

        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
                continue
            text_value = item.get("text")
            if item.get("type") == "text" and isinstance(text_value, str):
                text_parts.append(text_value)

        return "\n".join(part for part in text_parts if part).strip()
