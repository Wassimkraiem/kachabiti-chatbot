from __future__ import annotations

import asyncio
from pathlib import Path

from app.domain.models import ParsedSection
from app.infrastructure.parsers.base import BaseParser


class PdfParser(BaseParser):
    supported_extensions = {".pdf"}

    async def parse(self, path: Path) -> list[ParsedSection]:
        return await asyncio.to_thread(self._parse_sync, path)

    def _parse_sync(self, path: Path) -> list[ParsedSection]:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        sections: list[ParsedSection] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            sections.append(
                ParsedSection(
                    text=text,
                    metadata={"source_type": "pdf", "page_number": page_number},
                )
            )
        return sections

