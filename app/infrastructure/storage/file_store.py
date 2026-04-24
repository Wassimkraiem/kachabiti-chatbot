from __future__ import annotations

import asyncio
from pathlib import Path


class LocalFileStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, document_id: str, filename: str, content: bytes) -> Path:
        path = self._base_dir / f"{document_id}_{filename}"
        await asyncio.to_thread(path.write_bytes, content)
        return path

