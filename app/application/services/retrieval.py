from __future__ import annotations

from app.domain.interfaces import EmbeddingProvider, VectorStoreRepository
from app.domain.models import RetrievedChunk


class RetrievalService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def retrieve(self, query: str, limit: int) -> list[RetrievedChunk]:
        query_vector = await self._embedding_provider.embed_query(query)
        return await self._vector_store.search(query_vector=query_vector, limit=limit)

