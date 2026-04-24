from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_collection_inspection_service,
    get_qdrant_question_service,
    get_service_container,
)
from app.application.services.inspection import CollectionOverview, QdrantDocumentSummary, QdrantDocumentsOverview
from app.application.services.qdrant_questions import QdrantQuestion, QdrantQuestionsOverview
from app.domain.exceptions import NotFoundError, UnsupportedFileTypeError
from app.domain.models import ChatResult, Document, DocumentChunk, IngestionJob, IngestionStatus, RetrievedChunk, utcnow
from app.main import create_app


class FakeIngestionService:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.jobs: dict[str, IngestionJob] = {}
        self.allowed_extensions = {".txt", ".pdf", ".csv"}

    async def create_ingestion(self, filename: str, content_type: str, content: bytes):
        extension = f".{filename.rsplit('.', maxsplit=1)[-1].lower()}" if "." in filename else ""
        if extension not in self.allowed_extensions:
            raise UnsupportedFileTypeError(f"Unsupported file type '{extension}'.")

        document_id = f"doc-{len(self.documents) + 1}"
        job_id = f"job-{len(self.jobs) + 1}"
        document = Document(
            id=document_id,
            filename=filename,
            content_type=content_type,
            extension=extension,
            size_bytes=len(content),
            storage_path=f"/tmp/{filename}",
        )
        job = IngestionJob(id=job_id, document_id=document_id)
        self.documents[document_id] = document
        self.jobs[job_id] = job
        return document, job

    async def get_document(self, document_id: str) -> Document:
        if document_id not in self.documents:
            raise NotFoundError("missing document")
        return self.documents[document_id]

    async def get_job(self, job_id: str) -> IngestionJob:
        if job_id not in self.jobs:
            raise NotFoundError("missing job")
        return self.jobs[job_id]


class FakeProcessingService:
    def __init__(self, ingestion_service: FakeIngestionService) -> None:
        self._ingestion_service = ingestion_service
        self.processed: list[tuple[str, str]] = []

    async def process(self, document_id: str, job_id: str) -> None:
        self.processed.append((document_id, job_id))
        document = self._ingestion_service.documents[document_id]
        job = self._ingestion_service.jobs[job_id]
        document.status = IngestionStatus.COMPLETED
        document.updated_at = utcnow()
        job.status = IngestionStatus.COMPLETED
        job.processed_chunks = 3
        job.updated_at = utcnow()


class FakeChatService:
    async def complete(self, message: str, history, top_k=None) -> ChatResult:
        return ChatResult(
            answer=f"Grounded answer for: {message}",
            model="fake-model",
            sources=[
                RetrievedChunk(
                    id="chunk-1",
                    document_id="doc-1",
                    filename="guide.txt",
                    content="Relevant context",
                    score=0.97,
                    metadata={"page_number": 1},
                )
            ],
        )


class FakeReadinessDependency:
    async def ping(self) -> bool:
        return True

    async def is_configured(self) -> bool:
        return True


class FakeCollectionInspectionService:
    async def get_overview(self, limit: int = 200, offset: str | None = None) -> CollectionOverview:
        timestamp = utcnow()
        return CollectionOverview(
            collection_name="knowledge_base",
            documents=[
                Document(
                    id="doc-1",
                    filename="guide.txt",
                    content_type="text/plain",
                    extension=".txt",
                    size_bytes=128,
                    storage_path="/tmp/guide.txt",
                    status=IngestionStatus.COMPLETED,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            ],
            chunks=[
                DocumentChunk(
                    id="chunk-1",
                    document_id="doc-1",
                    filename="guide.txt",
                    content="Relevant context from the collection.",
                    chunk_index=0,
                    metadata={"section_index": 0},
                )
            ],
            total_documents=1,
            total_chunks=1,
            page_size=limit,
            next_offset=None,
            collection_exists=True,
            qdrant_available=True,
        )

    async def get_qdrant_documents(self, batch_size: int = 256) -> QdrantDocumentsOverview:
        timestamp = utcnow()
        return QdrantDocumentsOverview(
            collection_name="knowledge_base",
            documents=[
                QdrantDocumentSummary(
                    document_id="doc-1",
                    filename="guide.txt",
                    chunk_count=3,
                    status=IngestionStatus.COMPLETED.value,
                    content_type="text/plain",
                    extension=".txt",
                    size_bytes=128,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            ],
            total_documents=1,
            total_chunks=3,
            collection_exists=True,
            qdrant_available=True,
        )


class FakeQdrantQuestionService:
    def __init__(self) -> None:
        timestamp = utcnow()
        self.questions: dict[str, QdrantQuestion] = {
            "faq-1": QdrantQuestion(
                id="faq-1",
                question="How do I reset my password?",
                answer="Use the account settings page.",
                document_id="doc-qa",
                filename="faq.csv",
                chunk_index=0,
                source_type="qa_csv",
                updated_at=timestamp,
                metadata={"row_number": 1},
            )
        }

    async def list_questions(self, batch_size: int = 256) -> QdrantQuestionsOverview:
        del batch_size
        ordered = sorted(self.questions.values(), key=lambda item: item.id)
        return QdrantQuestionsOverview(
            collection_name="knowledge_base",
            questions=ordered,
            total_questions=len(ordered),
            collection_exists=True,
            qdrant_available=True,
        )

    async def search_questions(self, query: str, limit: int = 25) -> QdrantQuestionsOverview:
        tokens = [token for token in query.lower().split() if token]
        ranked: list[QdrantQuestion] = []
        for item in self.questions.values():
            haystack = f"{item.question} {item.answer}".lower()
            score = float(sum(1 for token in tokens if token in haystack))
            if score <= 0:
                continue
            ranked.append(
                QdrantQuestion(
                    id=item.id,
                    question=item.question,
                    answer=item.answer,
                    document_id=item.document_id,
                    filename=item.filename,
                    chunk_index=item.chunk_index,
                    source_type=item.source_type,
                    updated_at=item.updated_at,
                    score=score,
                    metadata=item.metadata,
                )
            )

        ranked.sort(key=lambda item: ((item.score or 0.0), item.question.lower()), reverse=True)
        return QdrantQuestionsOverview(
            collection_name="knowledge_base",
            questions=ranked[:limit],
            total_questions=min(len(ranked), limit),
            collection_exists=True,
            qdrant_available=True,
        )

    async def create_question(self, question: str, answer: str) -> QdrantQuestion:
        question_id = f"faq-{len(self.questions) + 1}"
        item = QdrantQuestion(
            id=question_id,
            question=question,
            answer=answer,
            document_id="faq-editor",
            filename="Qdrant FAQ",
            chunk_index=0,
            source_type="faq_editor",
            updated_at=utcnow(),
        )
        self.questions[question_id] = item
        return item

    async def update_question(self, question_id: str, question: str, answer: str) -> QdrantQuestion:
        if question_id not in self.questions:
            raise NotFoundError("missing question")
        current = self.questions[question_id]
        updated = QdrantQuestion(
            id=current.id,
            question=question,
            answer=answer,
            document_id=current.document_id,
            filename=current.filename,
            chunk_index=current.chunk_index,
            source_type=current.source_type,
            updated_at=utcnow(),
            metadata=current.metadata,
        )
        self.questions[question_id] = updated
        return updated

    async def delete_question(self, question_id: str) -> None:
        if question_id not in self.questions:
            raise NotFoundError("missing question")
        del self.questions[question_id]


@dataclass(slots=True)
class FakeContainer:
    ingestion_service: FakeIngestionService = field(default_factory=FakeIngestionService)
    chat_service: FakeChatService = field(default_factory=FakeChatService)
    embedding_provider: FakeReadinessDependency = field(default_factory=FakeReadinessDependency)
    chat_provider: FakeReadinessDependency = field(default_factory=FakeReadinessDependency)
    vector_store: FakeReadinessDependency = field(default_factory=FakeReadinessDependency)
    processing_service: FakeProcessingService | None = None

    def __post_init__(self) -> None:
        self.processing_service = FakeProcessingService(self.ingestion_service)


@pytest.fixture
def client():
    app = create_app()
    container = FakeContainer()
    question_service = FakeQdrantQuestionService()
    app.dependency_overrides[get_service_container] = lambda: container
    app.dependency_overrides[get_collection_inspection_service] = lambda: FakeCollectionInspectionService()
    app.dependency_overrides[get_qdrant_question_service] = lambda: question_service
    with TestClient(app) as test_client:
        yield test_client, container
