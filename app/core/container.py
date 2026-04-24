from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.application.services.chat import RagChatService
from app.application.services.ingestion import DocumentProcessingService, IngestionService
from app.application.services.retrieval import RetrievalService
from app.core.logging import configure_logging
from app.core.settings import Settings, get_settings
from app.infrastructure.ai.langsmith_integration import configure_langsmith_environment
from app.infrastructure.ai.openai_provider import OpenAIChatProvider, OpenAIEmbeddingProvider
from app.infrastructure.parsers.chunker import TextChunker
from app.infrastructure.parsers.csv_parser import CsvParser
from app.infrastructure.parsers.pdf_parser import PdfParser
from app.infrastructure.parsers.registry import ParserRegistry
from app.infrastructure.parsers.text_parser import TextParser
from app.infrastructure.repositories.file_metadata import JsonDocumentRepository, JsonIngestionJobRepository
from app.infrastructure.repositories.qdrant_vector_store import QdrantVectorStore
from app.infrastructure.storage.file_store import LocalFileStore


@dataclass(slots=True)
class ServiceContainer:
    settings: Settings
    ingestion_service: IngestionService
    processing_service: DocumentProcessingService
    retrieval_service: RetrievalService
    chat_service: RagChatService
    embedding_provider: OpenAIEmbeddingProvider
    chat_provider: OpenAIChatProvider
    vector_store: QdrantVectorStore


@lru_cache
def get_container() -> ServiceContainer:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_langsmith_environment(settings)

    document_repository = JsonDocumentRepository(settings.documents_dir)
    job_repository = JsonIngestionJobRepository(settings.jobs_dir)
    file_store = LocalFileStore(settings.uploads_dir)

    parser_registry = ParserRegistry([TextParser(), PdfParser(), CsvParser()])
    chunker = TextChunker(settings.chunk_size, settings.chunk_overlap)
    embedding_provider = OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key,
        model_name=settings.openai_embedding_model,
        base_url=settings.openai_base_url,
    )
    chat_provider = OpenAIChatProvider(
        api_key=settings.openai_api_key,
        model_name=settings.openai_chat_model,
        base_url=settings.openai_base_url,
        prompt_name=settings.langsmith_prompt_name,
        prompt_tag=settings.langsmith_prompt_tag,
    )
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection_name,
        dimensions=settings.embedding_dimensions,
        timeout_seconds=settings.qdrant_timeout_seconds,
    )

    ingestion_service = IngestionService(
        document_repository=document_repository,
        job_repository=job_repository,
        file_store=file_store,
        allowed_extensions=parser_registry.supported_extensions,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )
    processing_service = DocumentProcessingService(
        document_repository=document_repository,
        job_repository=job_repository,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
    retrieval_service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
    chat_service = RagChatService(
        retrieval_service=retrieval_service,
        chat_provider=chat_provider,
        default_top_k=settings.default_top_k,
    )

    return ServiceContainer(
        settings=settings,
        ingestion_service=ingestion_service,
        processing_service=processing_service,
        retrieval_service=retrieval_service,
        chat_service=chat_service,
        embedding_provider=embedding_provider,
        chat_provider=chat_provider,
        vector_store=vector_store,
    )
