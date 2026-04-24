from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app.api.dependencies import get_service_container
from app.api.schemas.documents import DocumentResponse, IngestDocumentResponse, IngestionJobResponse
from app.core.container import ServiceContainer

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post(
    "/documents:ingest",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and ingest a document",
)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    container: ServiceContainer = Depends(get_service_container),
) -> IngestDocumentResponse:
    payload = await file.read()
    document, job = await container.ingestion_service.create_ingestion(
        filename=file.filename or "upload.txt",
        content_type=file.content_type or "application/octet-stream",
        content=payload,
    )
    background_tasks.add_task(container.processing_service.process, document.id, job.id)
    return IngestDocumentResponse(document_id=document.id, job_id=job.id, status=job.status)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata",
)
async def get_document(
    document_id: str,
    container: ServiceContainer = Depends(get_service_container),
) -> DocumentResponse:
    document = await container.ingestion_service.get_document(document_id)
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        extension=document.extension,
        size_bytes=document.size_bytes,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        error=document.error,
    )


@router.get(
    "/ingestion-jobs/{job_id}",
    response_model=IngestionJobResponse,
    summary="Get ingestion job status",
)
async def get_ingestion_job(
    job_id: str,
    container: ServiceContainer = Depends(get_service_container),
) -> IngestionJobResponse:
    job = await container.ingestion_service.get_job(job_id)
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        processed_chunks=job.processed_chunks,
        error=job.error,
    )
