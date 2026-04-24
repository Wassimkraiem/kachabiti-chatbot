from __future__ import annotations

import asyncio
import csv
from pathlib import Path

from app.domain.models import ParsedSection
from app.infrastructure.parsers.base import BaseParser


class CsvParser(BaseParser):
    supported_extensions = {".csv"}

    async def parse(self, path: Path) -> list[ParsedSection]:
        return await asyncio.to_thread(self._parse_sync, path)

    def _parse_sync(self, path: Path) -> list[ParsedSection]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            sample = handle.read(2048)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
            except csv.Error:
                dialect = csv.excel

            reader = csv.reader(handle, dialect)
            rows = list(reader)

        if not rows:
            return []

        headers = rows[0]
        data_rows = rows[1:] if headers else rows
        sections: list[ParsedSection] = []
        for row_number, row in enumerate(data_rows, start=1):
            pairs = []
            for index, value in enumerate(row):
                column_name = headers[index] if index < len(headers) and headers[index] else f"column_{index + 1}"
                pairs.append(f"{column_name}: {value}")
            text = " | ".join(pairs)
            sections.append(
                ParsedSection(
                    text=text,
                    metadata={
                        "source_type": "csv",
                        "row_number": row_number,
                        "headers": headers,
                    },
                )
            )
        return sections

