from __future__ import annotations

import re
from uuid import uuid4

from app.domain.models import DocumentChunk, ParsedSection


class TextChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk(
        self,
        document_id: str,
        filename: str,
        sections: list[ParsedSection],
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section_index, section in enumerate(sections):
            normalized = re.sub(r"\s+", " ", section.text).strip()
            if not normalized:
                continue

            for content in self._slice_text(normalized):
                chunks.append(
                    DocumentChunk(
                        id=str(uuid4()),
                        document_id=document_id,
                        filename=filename,
                        content=content,
                        chunk_index=chunk_index,
                        metadata={
                            "section_index": section_index,
                            **section.metadata,
                        },
                    )
                )
                chunk_index += 1
        return chunks

    def _slice_text(self, text: str) -> list[str]:
        if len(text) <= self._chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self._chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(0, end - self._chunk_overlap)
        return chunks

