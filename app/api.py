"""Main API router and endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import DocumentCRUD, get_document_by_id
from app.crud import create_document as crud_create_document
from app.db import get_async_db
from app.ollama_client import OllamaClient
from app.progress import get_task_progress
from app.schemas import (
    DocumentCreateRequest,
    DocumentResponse,
    DocumentStatus,
    ExtractionRequest,
    ExtractionResponse,
    ProgressResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.tasks import (
    create_document_summarization_task,
    create_extraction_task,
    create_summarize_task,
)

api_router = APIRouter()
ollama_client = OllamaClient()


@api_router.post("/summarize", response_model=SummarizeResponse)
async def summarize_text(request: SummarizeRequest):
    """Summarize text using Ollama."""
    try:
        task_id = await create_summarize_task(
            text=request.text,
            model=request.model,
            max_length=request.max_length,
        )
        return SummarizeResponse(
            task_id=task_id,
            status="processing",
            message="Summarization task created successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create summarization task: {str(e)}",
        ) from e


@api_router.post("/extract", response_model=ExtractionResponse)
async def extract_content(request: ExtractionRequest):
    """Extract content from URL using Trafilatura."""
    try:
        task_id = await create_extraction_task(
            url=request.url,
            include_links=request.include_links,
            include_images=request.include_images,
        )
        return ExtractionResponse(
            task_id=task_id,
            status="processing",
            message="Extraction task created successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create extraction task: {str(e)}",
        ) from e


@api_router.get("/progress/{task_id}", response_model=ProgressResponse)
async def get_progress(task_id: str):
    """Get task progress."""
    try:
        progress = await get_task_progress(task_id)
        return progress
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {str(e)}"
        ) from e


@api_router.get("/models")
async def list_models():
    """List available Ollama models."""
    try:
        models = await ollama_client.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        ) from e


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@api_router.post("/documents/", response_model=DocumentResponse, status_code=202)
async def create_document(
    request: DocumentCreateRequest, db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new document with advanced uniqueness logic:
    - If exact name+URL match exists: re-trigger summarization
    - If partial match exists: return 409 Conflict
    - Otherwise: create new document
    """
    from app.logging_conf import get_logger

    logger = get_logger("api")
    name = request.name
    url = str(request.url)

    logger.info(f"POST /documents/ - name: '{name}', url: '{url}'")

    try:
        # =================================================================
        # STEP 1: Check for existing documents (race-safe via transaction)
        # =================================================================

        # Check for exact match (both name AND URL)
        exact_match = await DocumentCRUD.get_document_by_name_and_url(db, name, url)

        if exact_match:
            # EXACT MATCH: Re-trigger summarization
            logger.info(f"Exact match found for name+URL: {exact_match.id}")

            # Reset document for re-summarization
            document = await DocumentCRUD.reset_document_for_resummary(
                db, exact_match.id
            )
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to reset document for re-summarization",
                )

            # Enqueue new summarization job
            try:
                await create_document_summarization_task(document.id)
                logger.info(f"Re-summarization job enqueued for document {document.id}")
            except Exception as e:
                logger.error(f"Failed to enqueue re-summarization job: {str(e)}")

            return DocumentResponse(
                document_uuid=document.id,
                status=document.status,
                name=document.name,
                url=document.url,
                summary=document.summary,
                data_progress=document.data_progress,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )

        # Check for partial conflicts (name OR URL exists on different rows)
        name_conflict, url_conflict = await DocumentCRUD.find_conflicting_documents(
            db, name, url
        )

        # If we have conflicts, return 409
        if name_conflict and url_conflict:
            if name_conflict.id != url_conflict.id:
                # Both name and URL exist but on different documents
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict: Name '{name}' exists on document {name_conflict.id} and URL '{url}' exists on document {url_conflict.id}",
                )
            else:
                # Both name and URL exist on the same document - this should not happen
                # since we already checked for exact matches above, but handle it defensively
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict: Both name '{name}' and URL '{url}' already exist on document {name_conflict.id}",
                )
        elif name_conflict:
            # Only name exists on a different document
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Name '{name}' already exists on document {name_conflict.id}",
            )
        elif url_conflict:
            # Only URL exists on a different document
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: URL '{url}' already exists on document {url_conflict.id}",
            )

        # =================================================================
        # STEP 2: No conflicts - create new document (race-safe)
        # =================================================================

        try:
            # Use transaction to handle race conditions
            document = await crud_create_document(
                db=db, name=name, url=url, status=DocumentStatus.PENDING
            )
            logger.info(f"New document created: {document.id}")

        except IntegrityError as integrity_error:
            # Race condition: another request created the same document
            await db.rollback()
            logger.warning(
                f"IntegrityError caught, checking for race condition: {integrity_error}"
            )

            # Check if exact match now exists (created by concurrent request)
            exact_match = await DocumentCRUD.get_document_by_name_and_url(db, name, url)
            if exact_match:
                logger.info(
                    f"Race condition detected - exact match now exists: {exact_match.id}"
                )
                # Re-trigger summarization on the existing document
                document = await DocumentCRUD.reset_document_for_resummary(
                    db, exact_match.id
                )
                if document:
                    try:
                        await create_document_summarization_task(document.id)
                        logger.info(
                            "Re-summarization job enqueued after race condition"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to enqueue job after race condition: {str(e)}"
                        )

                    return DocumentResponse(
                        document_uuid=document.id,
                        status=document.status,
                        name=document.name,
                        url=document.url,
                        summary=document.summary,
                        data_progress=document.data_progress,
                        created_at=document.created_at,
                        updated_at=document.updated_at,
                    )

            # Check for new conflicts
            name_conflict, url_conflict = await DocumentCRUD.find_conflicting_documents(
                db, name, url
            )
            if name_conflict and url_conflict:
                if name_conflict.id != url_conflict.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Conflict: Name '{name}' exists on document {name_conflict.id} and URL '{url}' exists on document {url_conflict.id}",
                    )
                else:
                    # Both name and URL exist on the same document
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Conflict: Both name '{name}' and URL '{url}' already exist on document {name_conflict.id}",
                    )
            elif name_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict: Name '{name}' already exists on document {name_conflict.id}",
                )
            elif url_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflict: URL '{url}' already exists on document {url_conflict.id}",
                )

            # If we get here, it's an unexpected integrity error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database integrity error: {str(integrity_error)}",
            )

        # =================================================================
        # STEP 3: Enqueue summarization job for new document
        # =================================================================

        try:
            await create_document_summarization_task(document.id)
            logger.info(f"Summarization job enqueued for new document {document.id}")
        except Exception as e:
            logger.error(f"Failed to enqueue summarization job: {str(e)}")

        # Return 202 Accepted with document details
        return DocumentResponse(
            document_uuid=document.id,
            status=document.status,
            name=document.name,
            url=document.url,
            summary=document.summary,
            data_progress=document.data_progress,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@api_router.get("/documents/{document_uuid}/", response_model=DocumentResponse)
async def get_document(document_uuid: str, db: AsyncSession = Depends(get_async_db)):
    """Get document by UUID."""
    # Query document from database using CRUD function
    document = await get_document_by_id(db, document_uuid)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_uuid} not found",
        )

    return DocumentResponse(
        document_uuid=document.id,
        status=document.status,
        name=document.name,
        url=document.url,
        summary=document.summary,
        data_progress=document.data_progress,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@api_router.get("/")
async def api_info():
    """API information."""
    return {
        "name": "Summarizer API",
        "version": "0.1.0",
        "endpoints": {
            "documents": "/documents/",
            "summarize": "/summarize",
            "extract": "/extract",
            "progress": "/progress/{task_id}",
            "models": "/models",
            "health": "/health",
        },
    }
