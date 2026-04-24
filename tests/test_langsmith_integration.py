from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domain.models import ChatMessage, RetrievedChunk
from app.infrastructure.ai.langsmith_integration import (
    build_context_text,
    build_default_chat_prompt,
    inject_history,
    to_langchain_history,
)


def test_build_default_chat_prompt_uses_question_and_context_variables():
    prompt = build_default_chat_prompt()
    prompt_value = prompt.invoke({"question": "Where are you?", "context": "In Monastir."})
    messages = prompt_value.to_messages()

    assert isinstance(messages[0], SystemMessage)
    assert "Tunisian Darija" in messages[0].content
    assert isinstance(messages[1], HumanMessage)
    assert "Where are you?" in messages[1].content
    assert "In Monastir." in messages[1].content


def test_to_langchain_history_preserves_roles():
    history = [
        ChatMessage(role="system", content="system note"),
        ChatMessage(role="user", content="hello"),
        ChatMessage(role="assistant", content="hi"),
    ]

    messages = to_langchain_history(history)

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)


def test_inject_history_places_history_after_system_messages():
    prompt_messages = [
        SystemMessage(content="system"),
        HumanMessage(content="question"),
    ]
    history_messages = [
        HumanMessage(content="previous user"),
        AIMessage(content="previous assistant"),
    ]

    merged = inject_history(prompt_messages, history_messages)

    assert merged[0].content == "system"
    assert merged[1].content == "previous user"
    assert merged[2].content == "previous assistant"
    assert merged[3].content == "question"


def test_build_context_text_formats_retrieved_chunks():
    contexts = [
        RetrievedChunk(
            id="chunk-1",
            document_id="doc-1",
            filename="guide.txt",
            content="Relevant context",
            score=0.97,
            metadata={},
        )
    ]

    context_text = build_context_text(contexts)

    assert "[1] guide.txt score=0.9700" in context_text
    assert "Relevant context" in context_text
