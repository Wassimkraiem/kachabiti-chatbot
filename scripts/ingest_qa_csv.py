#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.application.services.qa_csv_import import QaCsvImportService
from app.core.settings import get_settings
from app.infrastructure.repositories.file_metadata import JsonDocumentRepository, JsonIngestionJobRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a CSV of question/answer pairs into the configured Qdrant collection."
    )
    parser.add_argument("csv_path", help="Path to the CSV file to import.")
    parser.add_argument(
        "--question-column",
        default="question",
        help="Header name for the question column. Defaults to 'question'.",
    )
    parser.add_argument(
        "--answer-column",
        default="answer",
        help="Header name for the answer column. Defaults to 'answer'.",
    )
    parser.add_argument(
        "--document-name",
        default=None,
        help="Optional display name to store in metadata instead of the CSV filename.",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    try:
        from app.infrastructure.ai.openai_provider import OpenAIEmbeddingProvider
        from app.infrastructure.repositories.qdrant_vector_store import QdrantVectorStore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Required runtime dependency is missing. Install the project dependencies before running the importer."
        ) from exc

    service = QaCsvImportService(
        document_repository=JsonDocumentRepository(settings.documents_dir),
        job_repository=JsonIngestionJobRepository(settings.jobs_dir),
        embedding_provider=OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model_name=settings.openai_embedding_model,
            base_url=settings.openai_base_url,
        ),
        vector_store=QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=settings.qdrant_timeout_seconds,
        ),
    )

    result = await service.import_csv(
        csv_path=Path(args.csv_path),
        question_column=args.question_column,
        answer_column=args.answer_column,
        document_name=args.document_name,
    )
    print(f"Imported {result.imported_chunks} Q/A rows into collection '{settings.qdrant_collection_name}'.")
    print(f"Document ID: {result.document.id}")
    print(f"Job ID: {result.job.id}")
    if result.skipped_rows:
        print(f"Skipped rows with missing question or answer: {result.skipped_rows}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Import interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
