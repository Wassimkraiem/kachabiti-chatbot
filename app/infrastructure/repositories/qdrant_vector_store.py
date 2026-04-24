from __future__ import annotations

from app.domain.exceptions import ConfigurationError
from app.domain.models import DocumentChunk, RetrievedChunk


class QdrantVectorStore:
    def __init__(
        self,
        url: str,
        collection_name: str,
        dimensions: int,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not url:
            raise ConfigurationError("QDRANT_URL is not configured.")

        from qdrant_client import AsyncQdrantClient, models

        self._client = AsyncQdrantClient(url=url, api_key=api_key, timeout=timeout_seconds)
        self._models = models
        self._collection_name = collection_name
        self._dimensions = dimensions

    async def ensure_collection(self) -> None:
        response = await self._client.get_collections()
        existing = {collection.name for collection in response.collections}
        if self._collection_name in existing:
            return

        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=self._models.VectorParams(
                size=self._dimensions,
                distance=self._models.Distance.COSINE,
            ),
        )

    async def upsert(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> None:
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            points.append(
                self._models.PointStruct(
                    id=chunk.id,
                    vector=vector,
                    payload={
                        "document_id": chunk.document_id,
                        "filename": chunk.filename,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        **chunk.metadata,
                    },
                )
            )

        await self._client.upsert(collection_name=self._collection_name, points=points)

    async def search(self, query_vector: list[float], limit: int) -> list[RetrievedChunk]:
        try:
            search_fn = getattr(self._client, "search", None)
            if callable(search_fn):
                hits = await search_fn(
                    collection_name=self._collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True,
                )
            else:
                query_points_fn = getattr(self._client, "query_points", None)
                if not callable(query_points_fn):
                    raise AttributeError("Qdrant client does not support search or query_points.")

                response = await query_points_fn(
                    collection_name=self._collection_name,
                    query=query_vector,
                    limit=limit,
                    with_payload=True,
                )
                hits = response.points
        except Exception as exc:
            if self._is_missing_collection_error(exc):
                await self.ensure_collection()
                return []
            raise

        results: list[RetrievedChunk] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                RetrievedChunk(
                    id=str(hit.id),
                    document_id=str(payload.get("document_id", "")),
                    filename=str(payload.get("filename", "unknown")),
                    content=str(payload.get("content", "")),
                    score=float(hit.score),
                    metadata={
                        key: value
                        for key, value in payload.items()
                        if key not in {"document_id", "filename", "content"}
                    },
                )
            )
        return results

    async def ping(self) -> bool:
        try:
            await self._client.get_collections()
        except Exception:
            return False
        return True

    def _is_missing_collection_error(self, exc: Exception) -> bool:
        message = str(exc)
        return (
            "Not found: Collection" in message
            and self._collection_name in message
            and "doesn't exist" in message
        )
