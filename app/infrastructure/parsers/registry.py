from __future__ import annotations

from pathlib import Path

from app.domain.exceptions import UnsupportedFileTypeError
from app.domain.interfaces import DocumentParser


class ParserRegistry:
    def __init__(self, parsers: list[DocumentParser]) -> None:
        self._parsers = parsers

    @property
    def supported_extensions(self) -> set[str]:
        extensions: set[str] = set()
        for parser in self._parsers:
            extensions.update(parser.supported_extensions)
        return extensions

    def get_parser(self, path: str | Path) -> DocumentParser:
        extension = Path(path).suffix.lower()
        for parser in self._parsers:
            if extension in parser.supported_extensions:
                return parser
        raise UnsupportedFileTypeError(f"Unsupported file type '{extension}'.")

