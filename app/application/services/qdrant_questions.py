from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.settings import Settings
from app.domain.exceptions import NotFoundError
from app.domain.interfaces import EmbeddingProvider

_FAQ_DOCUMENT_ID = "faq-editor"
_FAQ_FILENAME = "Qdrant FAQ"
_QUESTION_ANSWER_PATTERN = re.compile(r"^\s*Question:\s*(.*?)\nAnswer:\s*(.*)\s*$", re.DOTALL)


@dataclass(slots=True)
class QdrantQuestion:
    id: str
    question: str
    answer: str
    document_id: str
    filename: str
    chunk_index: int
    source_type: str | None = None
    updated_at: datetime | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QdrantQuestionsOverview:
    collection_name: str
    questions: list[QdrantQuestion]
    total_questions: int
    collection_exists: bool
    qdrant_available: bool
    qdrant_error: str | None = None


class QdrantQuestionService:
    def __init__(self, settings: Settings, embedding_provider: EmbeddingProvider) -> None:
        self._settings = settings
        self._embedding_provider = embedding_provider

    async def list_questions(self, batch_size: int = 256) -> QdrantQuestionsOverview:
        questions: list[QdrantQuestion] = []
        collection_exists = False
        qdrant_available = False
        qdrant_error: str | None = None

        client = None
        try:
            client = self._create_client()
            collections = await client.get_collections()
            qdrant_available = True
            collection_names = {collection.name for collection in collections.collections}
            collection_exists = self._settings.qdrant_collection_name in collection_names

            if collection_exists:
                offset: str | int | None = None
                while True:
                    page, page_offset = await client.scroll(
                        collection_name=self._settings.qdrant_collection_name,
                        limit=batch_size,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False,
                    )
                    for record in page:
                        question = self._record_to_question(record)
                        if question is not None:
                            questions.append(question)

                    if page_offset is None:
                        break
                    offset = page_offset
        except Exception as exc:
            qdrant_error = str(exc)
        finally:
            await self._close_client(client)

        questions.sort(
            key=lambda item: (
                item.updated_at is None,
                datetime.min if item.updated_at is None else item.updated_at,
                item.question.lower(),
            ),
            reverse=True,
        )
        return QdrantQuestionsOverview(
            collection_name=self._settings.qdrant_collection_name,
            questions=questions,
            total_questions=len(questions),
            collection_exists=collection_exists,
            qdrant_available=qdrant_available,
            qdrant_error=qdrant_error,
        )

    async def search_questions(self, query: str, limit: int = 25) -> QdrantQuestionsOverview:
        normalized_query = query.strip()
        if not normalized_query:
            return await self.list_questions(batch_size=limit)

        questions: list[QdrantQuestion] = []
        collection_exists = False
        qdrant_available = False
        qdrant_error: str | None = None

        client = None
        try:
            client = self._create_client()
            collections = await client.get_collections()
            qdrant_available = True
            collection_names = {collection.name for collection in collections.collections}
            collection_exists = self._settings.qdrant_collection_name in collection_names

            if collection_exists:
                query_vector = await self._embedding_provider.embed_query(normalized_query)
                hits = await self._search_question_records(
                    client=client,
                    query_vector=query_vector,
                    limit=limit,
                )
                for record in hits:
                    question = self._record_to_question(record)
                    if question is not None:
                        questions.append(question)
        except Exception as exc:
            qdrant_error = str(exc)
        finally:
            await self._close_client(client)

        return QdrantQuestionsOverview(
            collection_name=self._settings.qdrant_collection_name,
            questions=questions,
            total_questions=len(questions),
            collection_exists=collection_exists,
            qdrant_available=qdrant_available,
            qdrant_error=qdrant_error,
        )

    async def create_question(self, question: str, answer: str) -> QdrantQuestion:
        question_id = str(uuid4())
        return await self._upsert_question(
            question_id=question_id,
            question=question,
            answer=answer,
            existing_payload=None,
        )

    async def update_question(self, question_id: str, question: str, answer: str) -> QdrantQuestion:
        client = None
        try:
            client = self._create_client()
            record = await self._get_record_or_raise(client, question_id)
            return await self._upsert_question(
                question_id=str(record.id),
                question=question,
                answer=answer,
                existing_payload=record.payload or {},
                point_id=record.id,
            )
        finally:
            await self._close_client(client)

    async def delete_question(self, question_id: str) -> None:
        client = None
        try:
            client = self._create_client()
            await self._get_record_or_raise(client, question_id)

            from qdrant_client import models

            await client.delete(
                collection_name=self._settings.qdrant_collection_name,
                points_selector=models.PointIdsList(points=[self._coerce_point_id(question_id)]),
            )
        finally:
            await self._close_client(client)

    async def _upsert_question(
        self,
        question_id: str,
        question: str,
        answer: str,
        existing_payload: dict[str, Any] | None,
        point_id: str | int | None = None,
    ) -> QdrantQuestion:
        client = None
        try:
            client = self._create_client()
            await self._ensure_collection(client)

            payload = self._build_payload(question=question, answer=answer, existing_payload=existing_payload)
            content = payload["content"]
            [vector] = await self._embedding_provider.embed_documents([content])

            from qdrant_client import models

            await client.upsert(
                collection_name=self._settings.qdrant_collection_name,
                points=[
                    models.PointStruct(
                        id=self._coerce_point_id(question_id) if point_id is None else point_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

            stored = await self._get_record_or_raise(client, question_id)
            question_item = self._record_to_question(stored)
            if question_item is None:
                raise NotFoundError(f"Question '{question_id}' could not be parsed after saving.")
            return question_item
        finally:
            await self._close_client(client)

    async def _ensure_collection(self, client: Any) -> None:
        collections = await client.get_collections()
        existing = {collection.name for collection in collections.collections}
        if self._settings.qdrant_collection_name in existing:
            return

        from qdrant_client import models

        await client.create_collection(
            collection_name=self._settings.qdrant_collection_name,
            vectors_config=models.VectorParams(
                size=self._settings.embedding_dimensions,
                distance=models.Distance.COSINE,
            ),
        )

    async def _get_record_or_raise(self, client: Any, question_id: str) -> Any:
        records = await client.retrieve(
            collection_name=self._settings.qdrant_collection_name,
            ids=[self._coerce_point_id(question_id)],
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            raise NotFoundError(f"Question '{question_id}' was not found.")
        return records[0]

    async def _search_question_records(
        self,
        client: Any,
        query_vector: list[float],
        limit: int,
    ) -> list[Any]:
        from qdrant_client import models

        query_filter = self._build_question_filter(models)
        search_fn = getattr(client, "search", None)
        if callable(search_fn):
            try:
                return await search_fn(
                    collection_name=self._settings.qdrant_collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True,
                    query_filter=query_filter,
                )
            except TypeError:
                return await search_fn(
                    collection_name=self._settings.qdrant_collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True,
                    filter=query_filter,
                )

        query_points_fn = getattr(client, "query_points", None)
        if not callable(query_points_fn):
            raise AttributeError("Qdrant client does not support search or query_points.")

        try:
            response = await query_points_fn(
                collection_name=self._settings.qdrant_collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
                query_filter=query_filter,
            )
        except TypeError:
            response = await query_points_fn(
                collection_name=self._settings.qdrant_collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
                filter=query_filter,
            )
        return response.points

    def _build_question_filter(self, models: Any) -> Any:
        return models.Filter(
            should=[
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(value="faq_editor"),
                ),
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(value="qa_csv"),
                ),
            ]
        )

    def _build_payload(
        self,
        question: str,
        answer: str,
        existing_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        reserved = {
            "document_id",
            "filename",
            "content",
            "chunk_index",
            "question",
            "answer",
            "source_type",
            "updated_at",
        }
        preserved = {
            key: value
            for key, value in (existing_payload or {}).items()
            if key not in reserved
        }
        return {
            "document_id": str((existing_payload or {}).get("document_id") or _FAQ_DOCUMENT_ID),
            "filename": str((existing_payload or {}).get("filename") or _FAQ_FILENAME),
            "content": self._format_content(question, answer),
            "chunk_index": self._normalize_chunk_index((existing_payload or {}).get("chunk_index")),
            "question": question,
            "answer": answer,
            "source_type": str((existing_payload or {}).get("source_type") or "faq_editor"),
            "updated_at": datetime.now().isoformat(),
            **preserved,
        }

    def _record_to_question(self, record: Any) -> QdrantQuestion | None:
        payload = record.payload or {}
        question = str(payload.get("question", "")).strip()
        answer = str(payload.get("answer", "")).strip()
        if not question or not answer:
            question, answer = self._parse_content(str(payload.get("content", "")))
            if not question or not answer:
                return None

        metadata = {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "document_id",
                "filename",
                "content",
                "chunk_index",
                "question",
                "answer",
                "source_type",
                "updated_at",
            }
        }
        return QdrantQuestion(
            id=str(record.id),
            question=question,
            answer=answer,
            document_id=str(payload.get("document_id", "")),
            filename=str(payload.get("filename", "unknown")),
            chunk_index=self._normalize_chunk_index(payload.get("chunk_index")),
            source_type=self._string_or_none(payload.get("source_type")),
            updated_at=self._parse_datetime(payload.get("updated_at")),
            score=self._float_or_none(getattr(record, "score", None)),
            metadata=metadata,
        )

    def _parse_content(self, content: str) -> tuple[str, str]:
        match = _QUESTION_ANSWER_PATTERN.match(content)
        if match is None:
            return "", ""
        return match.group(1).strip(), match.group(2).strip()

    def _coerce_point_id(self, question_id: str) -> str | int:
        return int(question_id) if question_id.isdigit() else question_id

    def _normalize_chunk_index(self, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return 0
        return value

    def _string_or_none(self, value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    def _float_or_none(self, value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _format_content(self, question: str, answer: str) -> str:
        return f"Question: {question}\nAnswer: {answer}"

    def _create_client(self) -> Any:
        from qdrant_client import AsyncQdrantClient

        return AsyncQdrantClient(
            url=self._settings.qdrant_url,
            api_key=self._settings.qdrant_api_key,
            timeout=self._settings.qdrant_timeout_seconds,
        )

    async def _close_client(self, client: Any) -> None:
        if client is None:
            return
        close = getattr(client, "close", None)
        if not callable(close):
            return
        result = close()
        if inspect.isawaitable(result):
            await result
