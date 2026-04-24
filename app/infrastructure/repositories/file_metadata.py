from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable, Generic, TypeVar

from app.domain.exceptions import NotFoundError
from app.domain.models import Document, IngestionJob

T = TypeVar("T")


class JsonFileRepository(Generic[T]):
    def __init__(
        self,
        base_dir: Path,
        factory: Callable[[dict], T],
        serializer: Callable[[T], dict],
    ) -> None:
        self._base_dir = base_dir
        self._factory = factory
        self._serializer = serializer
        self._lock = asyncio.Lock()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, entity_id: str) -> Path:
        return self._base_dir / f"{entity_id}.json"

    async def save(self, entity: T) -> T:
        payload = self._serializer(entity)
        path = self._path(payload["id"])
        async with self._lock:
            await asyncio.to_thread(path.write_text, json.dumps(payload, indent=2), "utf-8")
        return entity

    async def get(self, entity_id: str) -> T:
        path = self._path(entity_id)
        if not path.exists():
            raise NotFoundError(f"Resource '{entity_id}' was not found.")

        data = await asyncio.to_thread(path.read_text, "utf-8")
        return self._factory(json.loads(data))


class JsonDocumentRepository(JsonFileRepository[Document]):
    def __init__(self, base_dir: Path) -> None:
        super().__init__(base_dir=base_dir, factory=Document.from_dict, serializer=lambda item: item.to_dict())


class JsonIngestionJobRepository(JsonFileRepository[IngestionJob]):
    def __init__(self, base_dir: Path) -> None:
        super().__init__(base_dir=base_dir, factory=IngestionJob.from_dict, serializer=lambda item: item.to_dict())

