from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_qdrant_question_service
from app.api.schemas.questions import (
    QdrantQuestionResponse,
    QdrantQuestionsResponse,
    QdrantQuestionWriteRequest,
)
from app.application.services.qdrant_questions import QdrantQuestionService

router = APIRouter(prefix="/api/v1/qdrant/questions", tags=["qdrant-questions"])


@router.get(
    "",
    response_model=QdrantQuestionsResponse,
    summary="List question/answer items currently stored in Qdrant",
)
async def list_qdrant_questions(
    batch_size: int = Query(default=256, ge=1, le=1000),
    query: str | None = Query(default=None, max_length=4000),
    question_service: QdrantQuestionService = Depends(get_qdrant_question_service),
) -> QdrantQuestionsResponse:
    overview = (
        await question_service.search_questions(query=query, limit=batch_size)
        if query is not None and query.strip()
        else await question_service.list_questions(batch_size=batch_size)
    )
    return QdrantQuestionsResponse(
        collection_name=overview.collection_name,
        questions=[
            QdrantQuestionResponse(
                id=item.id,
                question=item.question,
                answer=item.answer,
                document_id=item.document_id,
                filename=item.filename,
                chunk_index=item.chunk_index,
                source_type=item.source_type,
                updated_at=item.updated_at,
                score=item.score,
                metadata=item.metadata,
            )
            for item in overview.questions
        ],
        total_questions=overview.total_questions,
        collection_exists=overview.collection_exists,
        qdrant_available=overview.qdrant_available,
        qdrant_error=overview.qdrant_error,
    )


@router.post(
    "",
    response_model=QdrantQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a question/answer item in Qdrant",
)
async def create_qdrant_question(
    request: QdrantQuestionWriteRequest,
    question_service: QdrantQuestionService = Depends(get_qdrant_question_service),
) -> QdrantQuestionResponse:
    item = await question_service.create_question(question=request.question, answer=request.answer)
    return QdrantQuestionResponse(
        id=item.id,
        question=item.question,
        answer=item.answer,
        document_id=item.document_id,
        filename=item.filename,
        chunk_index=item.chunk_index,
        source_type=item.source_type,
        updated_at=item.updated_at,
        score=item.score,
        metadata=item.metadata,
    )


@router.put(
    "/{question_id}",
    response_model=QdrantQuestionResponse,
    summary="Update a question/answer item in Qdrant",
)
async def update_qdrant_question(
    question_id: str,
    request: QdrantQuestionWriteRequest,
    question_service: QdrantQuestionService = Depends(get_qdrant_question_service),
) -> QdrantQuestionResponse:
    item = await question_service.update_question(
        question_id=question_id,
        question=request.question,
        answer=request.answer,
    )
    return QdrantQuestionResponse(
        id=item.id,
        question=item.question,
        answer=item.answer,
        document_id=item.document_id,
        filename=item.filename,
        chunk_index=item.chunk_index,
        source_type=item.source_type,
        updated_at=item.updated_at,
        score=item.score,
        metadata=item.metadata,
    )


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question/answer item from Qdrant",
)
async def delete_qdrant_question(
    question_id: str,
    question_service: QdrantQuestionService = Depends(get_qdrant_question_service),
) -> Response:
    await question_service.delete_question(question_id=question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
