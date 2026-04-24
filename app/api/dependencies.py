from functools import lru_cache

from fastapi import Depends

from app.application.services.inspection import CollectionInspectionService
from app.application.services.qdrant_questions import QdrantQuestionService
from app.core.container import ServiceContainer, get_container
from app.core.settings import get_settings


def get_service_container() -> ServiceContainer:
    return get_container()


@lru_cache
def get_collection_inspection_service() -> CollectionInspectionService:
    return CollectionInspectionService(get_settings())


def get_qdrant_question_service(
    container: ServiceContainer = Depends(get_service_container),
) -> QdrantQuestionService:
    return QdrantQuestionService(
        settings=container.settings,
        embedding_provider=container.embedding_provider,
    )
