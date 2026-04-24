from __future__ import annotations

import asyncio
from pathlib import Path

from app.domain.models import ParsedSection
from app.infrastructure.parsers.base import BaseParser


class TextParser(BaseParser):
    supported_extensions = {".txt"}

    async def parse(self, path: Path) -> list[ParsedSection]:
        text = await asyncio.to_thread(path.read_text, "utf-8")
        return [ParsedSection(text=text, metadata={"source_type": "text"})]
