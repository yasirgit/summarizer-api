"""Progress tracking functionality for tasks and documents."""

import json
from datetime import datetime

from app.constants import DOCUMENT_STAGE_PROGRESS
from app.schemas import DocumentStatus, ProgressResponse
from app.settings import get_settings
from app.tasks import get_task_status

settings = get_settings()


async def get_task_progress(task_id: str) -> ProgressResponse:
    """Get task progress and status."""
    task_data = get_task_status(task_id)

    if not task_data:
        raise ValueError(f"Task {task_id} not found")

    # Parse timestamps
    created_at = datetime.fromisoformat(task_data["created_at"])
    updated_at = datetime.fromisoformat(task_data["updated_at"])

    # Determine progress message based on status
    status = task_data["status"]
    progress = task_data["progress"]

    if status == "pending":
        message = "Task is queued and waiting to be processed"
    elif status == "processing":
        if progress < 25:
            message = "Initializing task..."
        elif progress < 50:
            message = "Processing task..."
        elif progress < 75:
            message = "Finalizing task..."
        else:
            message = "Almost done..."
    elif status == "completed":
        message = "Task completed successfully"
    elif status == "failed":
        message = f"Task failed: {task_data.get('error_message', 'Unknown error')}"
    elif status == "cancelled":
        message = "Task was cancelled"
    else:
        message = f"Task status: {status}"

    return ProgressResponse(
        task_id=task_id,
        status=status,
        progress=progress,
        message=message,
        result=task_data.get("result"),
        created_at=created_at,
        updated_at=updated_at,
    )


async def get_task_summary(task_id: str) -> dict:
    """Get a summary of task information."""
    task_data = get_task_status(task_id)

    if not task_data:
        return {"error": "Task not found"}

    return {
        "id": task_id,
        "type": task_data["type"],
        "status": task_data["status"],
        "progress": task_data["progress"],
        "created_at": task_data["created_at"],
        "updated_at": task_data["updated_at"],
        "completed_at": task_data.get("completed_at"),
        "error_message": task_data.get("error_message"),
    }


async def get_tasks_by_status(status: str, limit: int = 100) -> list:
    """Get tasks filtered by status."""
    # This would typically query the database
    # For now, we'll return an empty list as this is a placeholder
    return []


async def get_tasks_by_type(task_type: str, limit: int = 100) -> list:
    """Get tasks filtered by type."""
    # This would typically query the database
    # For now, we'll return an empty list as this is a placeholder
    return []


async def get_recent_tasks(limit: int = 50) -> list:
    """Get recent tasks."""
    # This would typically query the database
    # For now, we'll return an empty list as this is a placeholder
    return []


async def get_task_statistics() -> dict:
    """Get overall task statistics."""
    # This would typically query the database
    # For now, we'll return placeholder statistics
    return {
        "total_tasks": 0,
        "pending_tasks": 0,
        "processing_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "cancelled_tasks": 0,
        "success_rate": 0.0,
        "average_processing_time": 0.0,
    }


async def cleanup_old_tasks(days_old: int = 7) -> int:
    """Clean up old completed/failed tasks."""
    # This would typically query the database and delete old records
    # For now, we'll return 0 as this is a placeholder
    return 0


async def export_task_data(task_id: str, format: str = "json") -> str:
    """Export task data in specified format."""
    task_data = get_task_status(task_id)

    if not task_data:
        raise ValueError(f"Task {task_id} not found")

    if format.lower() == "json":
        return json.dumps(task_data, indent=2, default=str)
    elif format.lower() == "csv":
        # Convert to CSV format
        # This is a simplified implementation
        csv_lines = []
        csv_lines.append("field,value")
        for key, value in task_data.items():
            if isinstance(value, dict):
                csv_lines.append(f"{key},{json.dumps(value)}")
            else:
                csv_lines.append(f"{key},{value}")
        return "\n".join(csv_lines)
    else:
        raise ValueError(f"Unsupported format: {format}")


async def get_task_performance_metrics(task_id: str) -> dict:
    """Get performance metrics for a specific task."""
    task_data = get_task_status(task_id)

    if not task_data:
        return {"error": "Task not found"}

    # Calculate performance metrics
    created_at = datetime.fromisoformat(task_data["created_at"])
    updated_at = datetime.fromisoformat(task_data["updated_at"])

    processing_time = None
    if task_data.get("completed_at"):
        completed_at = datetime.fromisoformat(task_data["completed_at"])
        processing_time = (completed_at - created_at).total_seconds()

    queue_time = None
    if task_data["status"] in ["processing", "completed", "failed"]:
        # This would need to be tracked separately in a real implementation
        queue_time = 0.0

    return {
        "task_id": task_id,
        "queue_time": queue_time,
        "processing_time": processing_time,
        "total_time": (updated_at - created_at).total_seconds(),
        "status": task_data["status"],
        "progress": task_data["progress"],
        "model_used": task_data.get("input_data", {}).get("model"),
        "input_size": len(str(task_data.get("input_data", {}))),
        "output_size": len(str(task_data.get("result", {}))),
    }


# Document progress helpers
def get_document_progress_for_stage(stage: DocumentStatus) -> float:
    """Get progress percentage for a document processing stage."""
    return DOCUMENT_STAGE_PROGRESS.get(stage, 0.0)


def get_document_stage_for_progress(progress: float) -> DocumentStatus:
    """Get document stage for a given progress percentage."""
    if progress >= 1.0:
        return DocumentStatus.SUCCESS
    elif progress >= 0.9:
        return DocumentStatus.SUMMARIZING
    elif progress >= 0.4:
        return DocumentStatus.PARSING
    elif progress >= 0.2:
        return DocumentStatus.FETCHING
    else:
        return DocumentStatus.PENDING
