"""Redis-based progress tracking for documents."""

import json
from datetime import datetime

import redis

from app.schemas import DocumentStatus
from app.settings import get_settings

settings = get_settings()
redis_conn = redis.from_url(settings.redis_url)


async def update_document_progress_redis(
    document_id: str,
    stage: DocumentStatus,
    progress: float = None,
    error_message: str = None,
) -> dict:
    """Update document progress and stage in Redis."""
    if progress is None:
        # Get progress from constants
        from app.constants import DOCUMENT_STAGE_PROGRESS

        progress = DOCUMENT_STAGE_PROGRESS.get(stage, 0.0)

    # Store progress in Redis for real-time updates
    progress_data = {
        "document_id": document_id,
        "stage": stage,
        "progress": progress,
        "timestamp": datetime.utcnow().isoformat(),
        "error_message": error_message,
    }

    redis_conn.setex(
        f"doc_progress:{document_id}",
        3600,
        json.dumps(progress_data),  # TTL: 1 hour
    )

    return progress_data


async def get_document_progress_redis(document_id: str) -> dict:
    """Get current document progress from Redis."""
    progress_data = redis_conn.get(f"doc_progress:{document_id}")
    if progress_data:
        return json.loads(progress_data.decode())
    return None
