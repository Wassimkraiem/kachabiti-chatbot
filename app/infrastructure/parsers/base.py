from __future__ import annotations

from pathlib import Path

from app.domain.models import ParsedSection


class BaseParser:
    supported_extensions: set[str] = set()

    async def parse(self, path: Path) -> list[ParsedSection]:
        raise NotImplementedError

