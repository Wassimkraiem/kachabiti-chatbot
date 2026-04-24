from app.domain.models import ParsedSection
from app.infrastructure.parsers.chunker import TextChunker


def test_chunker_splits_long_sections_with_overlap():
    chunker = TextChunker(chunk_size=20, chunk_overlap=5)
    sections = [ParsedSection(text="abcdefghijklmnopqrstuvwxyz")]

    chunks = chunker.chunk(document_id="doc-1", filename="alpha.txt", sections=sections)

    assert len(chunks) == 2
    assert chunks[0].content == "abcdefghijklmnopqrst"
    assert chunks[1].content.startswith("pqrst")
