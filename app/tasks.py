"""Task management functionality using Redis and RQ."""

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis
from rq import Queue
from rq.job import Job

from app.constants import DOCUMENT_STAGE_PROGRESS
from app.crud import (
    get_document_by_id,
    update_document_error,
    update_document_progress,
    update_document_status,
    update_document_summary,
)
from app.extraction import ContentExtractor, extract_content_from_url
from app.ollama_client import OllamaClient
from app.redis_progress import (
    update_document_progress_redis,
)
from app.schemas import DocumentStatus
from app.settings import get_settings

settings = get_settings()

# Redis connection
redis_conn = redis.from_url(settings.redis_url)
task_queue = Queue(connection=redis_conn)

# Ollama client
ollama_client = OllamaClient()


def create_task_id() -> str:
    """Create a unique task ID."""
    return str(uuid4())


async def create_summarize_task(
    text: str,
    model: str | None = None,
    max_length: int | None = None,
    language: str = "en",
) -> str:
    """Create a summarization task."""
    task_id = create_task_id()

    # Store task metadata in Redis
    task_data = {
        "id": task_id,
        "type": "summarize",
        "status": "pending",
        "progress": 0.0,
        "input_data": {
            "text": text,
            "model": model or settings.ollama_model,
            "max_length": max_length,
            "language": language,
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    redis_conn.setex(f"task:{task_id}", 3600, json.dumps(task_data))  # 1 hour TTL

    # Queue the task
    job = task_queue.enqueue(
        summarize_text_worker,
        task_id,
        text,
        model,
        max_length,
        language,
        job_timeout="15m",
    )

    # Store job ID for tracking
    redis_conn.setex(f"job:{task_id}", 3600, job.id)

    return task_id


async def create_extraction_task(
    url: str,
    include_links: bool = True,
    include_images: bool = False,
    language: str = "en",
) -> str:
    """Create a content extraction task."""
    task_id = create_task_id()

    # Store task metadata in Redis
    task_data = {
        "id": task_id,
        "type": "extract",
        "status": "pending",
        "progress": 0.0,
        "input_data": {
            "url": url,
            "include_links": include_links,
            "include_images": include_images,
            "language": language,
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    redis_conn.setex(f"task:{task_id}", 3600, json.dumps(task_data))  # 1 hour TTL

    # Queue the task
    job = task_queue.enqueue(
        extract_content_worker,
        task_id,
        url,
        include_links,
        include_images,
        language,
        job_timeout="5m",
    )

    # Store job ID for tracking
    redis_conn.setex(f"job:{job.id}", 3600, job.id)

    return task_id


def update_task_progress(
    task_id: str,
    status: str,
    progress: float,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
):
    """Update task progress in Redis."""
    task_key = f"task:{task_id}"
    task_data = redis_conn.get(task_key)

    if task_data:
        task = json.loads(task_data)
        task["status"] = status
        task["progress"] = progress
        task["updated_at"] = datetime.utcnow().isoformat()

        if result:
            task["result"] = result

        if error_message:
            task["error_message"] = error_message

        if status in ["completed", "failed"]:
            task["completed_at"] = datetime.utcnow().isoformat()

        # Update TTL
        redis_conn.setex(task_key, 3600, json.dumps(task))


def summarize_text_worker(
    task_id: str,
    text: str,
    model: str | None,
    max_length: int | None,
    language: str,
):
    """Worker function for text summarization."""
    try:
        # Update progress
        update_task_progress(task_id, "processing", 25.0)

        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Summarize text using Ollama
            update_task_progress(task_id, "processing", 50.0)

            summary = loop.run_until_complete(
                ollama_client.summarize_text(
                    text=text, model=model, max_length=max_length, language=language
                )
            )

            update_task_progress(task_id, "processing", 75.0)

            # Prepare result
            result = {
                "summary": summary,
                "original_length": len(text),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(text) if text else 0,
                "model_used": model or settings.ollama_model,
                "language": language,
            }

            # Update task as completed
            update_task_progress(task_id, "completed", 100.0, result=result)

        finally:
            loop.close()

    except Exception as e:
        # Update task as failed
        update_task_progress(task_id, "failed", 0.0, error_message=str(e))
        raise


def extract_content_worker(
    task_id: str, url: str, include_links: bool, include_images: bool, language: str
):
    """Worker function for content extraction."""
    try:
        # Update progress
        update_task_progress(task_id, "processing", 25.0)

        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Extract content
            update_task_progress(task_id, "processing", 50.0)

            extracted_content = loop.run_until_complete(
                extract_content_from_url(
                    url=url,
                    include_links=include_links,
                    include_images=include_images,
                    language=language,
                )
            )

            update_task_progress(task_id, "processing", 75.0)

            # Prepare result
            result = {
                "extracted_content": extracted_content,
                "url": url,
                "extraction_options": {
                    "include_links": include_links,
                    "include_images": include_images,
                    "language": language,
                },
            }

            # Update task as completed
            update_task_progress(task_id, "completed", 100.0, result=result)

        finally:
            loop.close()

    except Exception as e:
        # Update task as failed
        update_task_progress(task_id, "failed", 0.0, error_message=str(e))
        raise


def get_task_status(task_id: str) -> dict[str, Any] | None:
    """Get task status from Redis."""
    task_key = f"task:{task_id}"
    task_data = redis_conn.get(task_key)

    if task_data:
        return json.loads(task_data)
    return None


def cancel_task(task_id: str) -> bool:
    """Cancel a running task."""
    job_id = redis_conn.get(f"job:{task_id}")

    if job_id:
        job = Job.fetch(job_id.decode(), connection=redis_conn)
        if job.is_started:
            job.cancel()
            update_task_progress(task_id, "cancelled", 0.0)
            return True

    return False


def cleanup_completed_tasks():
    """Clean up completed tasks older than 24 hours."""
    # This would be implemented based on your specific cleanup requirements
    pass


async def create_document_summarization_task(document_id: str) -> str:
    """Create a document summarization task with idempotency check."""

    # Check for existing job in progress (idempotency)
    existing_job_key = f"doc_job:{document_id}"
    existing_job_id = redis_conn.get(existing_job_key)

    if existing_job_id:
        # Check if the job is still active
        try:
            existing_job = Job.fetch(existing_job_id.decode(), connection=redis_conn)
            if existing_job.get_status() in ["queued", "started"]:
                print(
                    f"Skipping duplicate job for document {document_id}, existing job: {existing_job_id.decode()}"
                )
                return existing_job_id.decode()
        except Exception:
            # Job not found or invalid, continue with creating new job
            pass

    task_id = create_task_id()

    # Store task metadata in Redis
    task_data = {
        "id": task_id,
        "type": "document_summarize",
        "document_id": document_id,
        "status": "pending",
        "progress": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    redis_conn.setex(f"task:{task_id}", 3600, json.dumps(task_data))  # 1 hour TTL

    # Queue the task with extended timeout to accommodate Ollama processing
    job = task_queue.enqueue(summarize_document_worker, document_id, job_timeout="20m")

    # Store job ID for tracking and idempotency
    redis_conn.setex(f"job:{task_id}", 3600, job.id)
    redis_conn.setex(existing_job_key, 3600, job.id)  # Track active job per document

    return task_id


def summarize_document_worker(document_id: str):
    """Worker function for document summarization pipeline."""
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run the async document summarization
            loop.run_until_complete(summarize_document(document_id))
        finally:
            loop.close()

    except Exception as error:
        # Update document as failed - use synchronous Redis update instead of async DB
        try:
            # Update progress in Redis to show failure
            update_document_progress_redis(
                document_id, 
                DocumentStatus.FAILED, 
                error_message=str(error)
            )
            print(f"Document {document_id} failed: {str(error)}")
        except Exception as update_error:
            print(f"Failed to update error status: {update_error}")
        raise


async def summarize_document(document_id: str):
    """Document summarization pipeline that advances through stages with comprehensive error handling."""
    from app.db import get_async_db
    from app.logging_conf import get_logger

    logger = get_logger("document_pipeline")
    logger.info(f"Starting document summarization pipeline for {document_id}")

    async for db in get_async_db():
        document = await get_document_by_id(db, document_id)
        if not document:
            error_msg = f"Document {document_id} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Check if document is already in a terminal state (idempotency at document level)
        if document.status in [DocumentStatus.SUCCESS, DocumentStatus.FAILED]:
            logger.info(
                f"Document {document_id} already in terminal state: {document.status}"
            )
            return

        try:
            # =================================================================
            # STAGE 1: FETCHING - Download page and update progress
            # =================================================================
            logger.info(
                f"[{document_id}] Stage 1: FETCHING - Downloading content from {document.url}"
            )

            await update_document_status(db, document_id, DocumentStatus.FETCHING)
            await update_document_progress(
                db, document_id, DOCUMENT_STAGE_PROGRESS[DocumentStatus.FETCHING]
            )
            await update_document_progress_redis(document_id, DocumentStatus.FETCHING)

            # Extract content from URL
            async with ContentExtractor() as extractor:
                extracted_content = await extractor.extract_content_from_url(
                    document.url
                )

            logger.info(
                f"[{document_id}] FETCHING completed: {len(extracted_content)} chars extracted"
            )

            # =================================================================
            # STAGE 2: PARSING - Extract text and update progress; error if empty
            # =================================================================
            logger.info(
                f"[{document_id}] Stage 2: PARSING - Processing extracted content"
            )

            await update_document_status(db, document_id, DocumentStatus.PARSING)
            await update_document_progress(
                db, document_id, DOCUMENT_STAGE_PROGRESS[DocumentStatus.PARSING]
            )
            await update_document_progress_redis(document_id, DocumentStatus.PARSING)

            # Parse and clean the extracted content
            async with ContentExtractor() as extractor:
                parsed_content = extractor.clean_content(extracted_content)

            # Validate content is not empty
            if not parsed_content or len(parsed_content.strip()) < 10:
                error_msg = f"Parsed content is empty or too short (length: {len(parsed_content) if parsed_content else 0})"
                logger.error(f"[{document_id}] PARSING failed: {error_msg}")
                raise ValueError(error_msg)

            logger.info(
                f"[{document_id}] PARSING completed: {len(parsed_content)} chars of clean content"
            )

            # =================================================================
            # STAGE 3: SUMMARIZING - Call Ollama and store summary (≤1500 chars)
            # =================================================================
            logger.info(
                f"[{document_id}] Stage 3: SUMMARIZING - Generating summary with Ollama"
            )

            await update_document_status(db, document_id, DocumentStatus.SUMMARIZING)
            await update_document_progress(
                db,
                document_id,
                DOCUMENT_STAGE_PROGRESS[DocumentStatus.SUMMARIZING],
            )
            await update_document_progress_redis(
                document_id, DocumentStatus.SUMMARIZING
            )

            # Generate summary with length validation
            summary = await ollama_client.summarize(
                text=parsed_content, language_hint="en"
            )

            # Enforce 1500 character limit
            if len(summary) > 1500:
                logger.warning(
                    f"[{document_id}] Summary too long ({len(summary)} chars), trimming to 1500"
                )
                # Trim at sentence boundary (handled by ollama_client._trim_to_sentence_boundary)
                summary = ollama_client._trim_to_sentence_boundary(summary, 1500)

            logger.info(
                f"[{document_id}] SUMMARIZING completed: {len(summary)} chars summary generated"
            )

            # =================================================================
            # STAGE 4: SUCCESS - Set progress to 1.0 and save summary
            # =================================================================
            logger.info(f"[{document_id}] Stage 4: SUCCESS - Finalizing document")

            await update_document_summary(db, document_id, summary)
            await update_document_status(db, document_id, DocumentStatus.SUCCESS)
            await update_document_progress(
                db,
                document_id,
                1.0,  # Explicitly set to 1.0 for SUCCESS
            )
            await update_document_progress_redis(document_id, DocumentStatus.SUCCESS)

            logger.info(f"[{document_id}] Pipeline completed successfully")

        except Exception as e:
            # =================================================================
            # ERROR HANDLING - Set FAILED status and record last_error
            # =================================================================
            error_msg = str(e)
            logger.error(f"[{document_id}] Pipeline failed: {error_msg}")

            try:
                # Update document as failed with error details
                await update_document_error(db, document_id, error_msg)
                await update_document_status(db, document_id, DocumentStatus.FAILED)
                await update_document_progress_redis(
                    document_id, DocumentStatus.FAILED, error_message=error_msg
                )
                logger.info(f"[{document_id}] Error status updated in database")
            except Exception as update_error:
                logger.error(
                    f"[{document_id}] Failed to update error status: {update_error}"
                )

            # Clean up idempotency lock
            try:
                redis_conn.delete(f"doc_job:{document_id}")
            except Exception:
                pass

            raise

        finally:
            # Clean up idempotency lock on completion
            try:
                redis_conn.delete(f"doc_job:{document_id}")
            except Exception:
                pass
