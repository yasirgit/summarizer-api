"""Constants for the application."""

from app.schemas import DocumentStatus

# Progress constants for document processing stages
DOCUMENT_STAGE_PROGRESS = {
    DocumentStatus.PENDING: 0.0,
    DocumentStatus.FETCHING: 0.2,
    DocumentStatus.PARSING: 0.4,
    DocumentStatus.SUMMARIZING: 0.9,
    DocumentStatus.SUCCESS: 1.0,
    DocumentStatus.FAILED: 0.0,
}

# Progress constants for task processing stages
TASK_STAGE_PROGRESS = {
    "pending": 0.0,
    "processing": 0.5,
    "completed": 1.0,
    "failed": 0.0,
}
