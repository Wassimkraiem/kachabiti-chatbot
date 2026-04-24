from __future__ import annotations

import logging
import os

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.core.settings import Settings
from app.domain.models import ChatMessage, RetrievedChunk

logger = logging.getLogger(__name__)

DEFAULT_CHAT_SYSTEM_PROMPT = (
    "You are a retrieval-augmented assistant that helps answer user questions. "
    "Always respond only in Tunisian Darija. "
    "Answer only from the provided context. "
    "If the context is insufficient, say so clearly in Tunisian Darija and do not invent facts."
)

DEFAULT_CHAT_USER_PROMPT = (
    "Question:\n{question}\n\n"
    "Retrieved context:\n{context}\n\n"
    "Respond with a concise, grounded answer."
)


def configure_langsmith_environment(settings: Settings) -> None:
    os.environ["LANGSMITH_TRACING"] = "true" if settings.langsmith_tracing else "false"

    variable_map = {
        "LANGSMITH_API_KEY": settings.langsmith_api_key,
        "LANGSMITH_ENDPOINT": settings.langsmith_endpoint,
        "LANGSMITH_PROJECT": settings.langsmith_project,
        "LANGSMITH_WORKSPACE_ID": settings.langsmith_workspace_id,
    }
    for key, value in variable_map.items():
        if value:
            os.environ[key] = value


def build_default_chat_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", DEFAULT_CHAT_SYSTEM_PROMPT),
            ("human", DEFAULT_CHAT_USER_PROMPT),
        ]
    )


def load_chat_prompt(prompt_name: str | None, prompt_tag: str = "latest"):
    clean_name = (prompt_name or "").strip()
    if not clean_name:
        return build_default_chat_prompt(), "code"

    prompt_ref = clean_name if not prompt_tag else f"{clean_name}:{prompt_tag}"
    try:
        from langsmith import Client

        prompt = Client().pull_prompt(prompt_ref)
        logger.info("Loaded chat prompt from LangSmith", extra={"prompt_ref": prompt_ref})
        return prompt, prompt_ref
    except Exception:
        logger.warning(
            "Falling back to the in-code prompt because the LangSmith prompt could not be loaded.",
            extra={"prompt_ref": prompt_ref},
        )
        return build_default_chat_prompt(), "code"


def describe_prompt_messages(prompt: object) -> list[dict[str, str]]:
    messages = getattr(prompt, "messages", None)
    if not isinstance(messages, list):
        return [{"role": "unknown", "content": str(prompt)}]

    return [
        {
            "role": _prompt_message_role(item),
            "content": _prompt_message_content(item),
        }
        for item in messages
    ]


def build_context_text(contexts: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{index}] {chunk.filename} score={chunk.score:.4f}\n{chunk.content}"
        for index, chunk in enumerate(contexts, start=1)
    )


def to_langchain_history(history: list[ChatMessage]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in history:
        if item.role == "system":
            messages.append(SystemMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
        else:
            messages.append(HumanMessage(content=item.content))
    return messages


def inject_history(prompt_messages: list[BaseMessage], history_messages: list[BaseMessage]) -> list[BaseMessage]:
    if not history_messages:
        return prompt_messages

    system_prefix_length = 0
    while system_prefix_length < len(prompt_messages) and isinstance(prompt_messages[system_prefix_length], SystemMessage):
        system_prefix_length += 1

    return [
        *prompt_messages[:system_prefix_length],
        *history_messages,
        *prompt_messages[system_prefix_length:],
    ]


def _prompt_message_role(item: object) -> str:
    class_name = item.__class__.__name__.lower()
    if "system" in class_name:
        return "system"
    if "human" in class_name:
        return "user"
    if "ai" in class_name or "assistant" in class_name:
        return "assistant"
    if "placeholder" in class_name:
        return "placeholder"
    return "unknown"


def _prompt_message_content(item: object) -> str:
    prompt = getattr(item, "prompt", None)
    if prompt is not None:
        template = getattr(prompt, "template", None)
        if isinstance(template, str):
            return template
    content = getattr(item, "content", None)
    if isinstance(content, str):
        return content
    variable_name = getattr(item, "variable_name", None)
    if isinstance(variable_name, str):
        return "{" + variable_name + "}"
    return str(item)
