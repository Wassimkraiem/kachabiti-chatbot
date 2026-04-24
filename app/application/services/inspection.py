from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.settings import Settings
from app.domain.models import Document, DocumentChunk


@dataclass(slots=True)
class CollectionOverview:
    collection_name: str
    documents: list[Document]
    chunks: list[DocumentChunk]
    total_documents: int
    total_chunks: int
    page_size: int
    next_offset: str | None
    collection_exists: bool
    qdrant_available: bool
    qdrant_error: str | None = None


@dataclass(slots=True)
class QdrantDocumentSummary:
    document_id: str
    filename: str
    chunk_count: int
    status: str | None = None
    content_type: str | None = None
    extension: str | None = None
    size_bytes: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    error: str | None = None


@dataclass(slots=True)
class QdrantDocumentsOverview:
    collection_name: str
    documents: list[QdrantDocumentSummary]
    total_documents: int
    total_chunks: int
    collection_exists: bool
    qdrant_available: bool
    qdrant_error: str | None = None


class CollectionInspectionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_overview(self, limit: int = 200, offset: str | None = None) -> CollectionOverview:
        documents = await asyncio.to_thread(self._load_documents)
        chunks: list[DocumentChunk] = []
        total_chunks = 0
        next_offset: str | None = None
        collection_exists = False
        qdrant_available = False
        qdrant_error: str | None = None

        client = None
        try:
            from qdrant_client import AsyncQdrantClient

            client = AsyncQdrantClient(
                url=self._settings.qdrant_url,
                api_key=self._settings.qdrant_api_key,
                timeout=self._settings.qdrant_timeout_seconds,
            )
            collections = await client.get_collections()
            qdrant_available = True
            collection_names = {collection.name for collection in collections.collections}
            collection_exists = self._settings.qdrant_collection_name in collection_names

            if collection_exists:
                count_result = await client.count(
                    collection_name=self._settings.qdrant_collection_name,
                    exact=True,
                )
                total_chunks = count_result.count
                page, page_offset = await client.scroll(
                    collection_name=self._settings.qdrant_collection_name,
                    limit=limit,
                    offset=self._parse_offset(offset),
                    with_payload=True,
                    with_vectors=False,
                )
                chunks = [self._record_to_chunk(record) for record in page]
                next_offset = None if page_offset is None else str(page_offset)
        except Exception as exc:
            qdrant_error = str(exc)
        finally:
            if client is not None:
                close = getattr(client, "close", None)
                if callable(close):
                    result = close()
                    if inspect.isawaitable(result):
                        await result

        return CollectionOverview(
            collection_name=self._settings.qdrant_collection_name,
            documents=documents,
            chunks=chunks,
            total_documents=len(documents),
            total_chunks=total_chunks,
            page_size=limit,
            next_offset=next_offset,
            collection_exists=collection_exists,
            qdrant_available=qdrant_available,
            qdrant_error=qdrant_error,
        )

    async def get_qdrant_documents(self, batch_size: int = 256) -> QdrantDocumentsOverview:
        documents = await asyncio.to_thread(self._load_documents)
        documents_by_id = {document.id: document for document in documents}
        grouped: dict[str, QdrantDocumentSummary] = {}
        total_chunks = 0
        collection_exists = False
        qdrant_available = False
        qdrant_error: str | None = None

        client = None
        try:
            from qdrant_client import AsyncQdrantClient

            client = AsyncQdrantClient(
                url=self._settings.qdrant_url,
                api_key=self._settings.qdrant_api_key,
                timeout=self._settings.qdrant_timeout_seconds,
            )
            collections = await client.get_collections()
            qdrant_available = True
            collection_names = {collection.name for collection in collections.collections}
            collection_exists = self._settings.qdrant_collection_name in collection_names

            if collection_exists:
                count_result = await client.count(
                    collection_name=self._settings.qdrant_collection_name,
                    exact=True,
                )
                total_chunks = count_result.count

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
                        payload = record.payload or {}
                        document_id = str(payload.get("document_id", "")).strip()
                        if not document_id:
                            continue

                        filename = str(payload.get("filename", "unknown"))
                        summary = grouped.get(document_id)
                        if summary is None:
                            local_document = documents_by_id.get(document_id)
                            summary = QdrantDocumentSummary(
                                document_id=document_id,
                                filename=local_document.filename if local_document else filename,
                                chunk_count=0,
                                status=None if local_document is None else local_document.status.value,
                                content_type=None if local_document is None else local_document.content_type,
                                extension=None if local_document is None else local_document.extension,
                                size_bytes=None if local_document is None else local_document.size_bytes,
                                created_at=None if local_document is None else local_document.created_at,
                                updated_at=None if local_document is None else local_document.updated_at,
                                error=None if local_document is None else local_document.error,
                            )
                            grouped[document_id] = summary

                        summary.chunk_count += 1
                        if summary.filename == "unknown" and filename:
                            summary.filename = filename

                    if page_offset is None:
                        break
                    offset = page_offset
        except Exception as exc:
            qdrant_error = str(exc)
        finally:
            if client is not None:
                close = getattr(client, "close", None)
                if callable(close):
                    result = close()
                    if inspect.isawaitable(result):
                        await result

        ordered_documents = sorted(
            grouped.values(),
            key=lambda item: (-item.chunk_count, item.filename.lower(), item.document_id),
        )
        return QdrantDocumentsOverview(
            collection_name=self._settings.qdrant_collection_name,
            documents=ordered_documents,
            total_documents=len(ordered_documents),
            total_chunks=total_chunks,
            collection_exists=collection_exists,
            qdrant_available=qdrant_available,
            qdrant_error=qdrant_error,
        )

    def _load_documents(self) -> list[Document]:
        documents_dir = self._settings.documents_dir
        if not documents_dir.exists():
            return []

        documents: list[Document] = []
        for path in sorted(documents_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text("utf-8"))
                documents.append(Document.from_dict(payload))
            except Exception:
                continue

        documents.sort(key=lambda item: item.updated_at, reverse=True)
        return documents

    def _record_to_chunk(self, record: Any) -> DocumentChunk:
        payload = record.payload or {}
        metadata = {
            key: value
            for key, value in payload.items()
            if key not in {"document_id", "filename", "content", "chunk_index"}
        }
        chunk_index = payload.get("chunk_index")
        if isinstance(chunk_index, bool) or not isinstance(chunk_index, int):
            chunk_index = -1

        return DocumentChunk(
            id=str(record.id),
            document_id=str(payload.get("document_id", "")),
            filename=str(payload.get("filename", "unknown")),
            content=str(payload.get("content", "")),
            chunk_index=chunk_index,
            metadata=metadata,
        )

    def _parse_offset(self, offset: str | None) -> str | int | None:
        if offset is None or offset == "":
            return None
        if offset.isdigit():
            return int(offset)
        return offset
