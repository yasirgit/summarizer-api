"""Pydantic schemas for request and response models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, validator


class DocumentStatus(str, Enum):
    """Document processing status enum."""

    PENDING = "PENDING"
    FETCHING = "FETCHING"
    PARSING = "PARSING"
    SUMMARIZING = "SUMMARIZING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DocumentCreateRequest(BaseModel):
    """Request schema for creating a document."""

    name: str = Field(..., min_length=1, max_length=255, description="Document name")
    url: HttpUrl = Field(..., description="Document URL")

    @validator("url")
    def validate_url_scheme(cls, v):
        if v.scheme not in ["http", "https"]:
            raise ValueError("URL must use HTTP or HTTPS scheme")
        return v


class DocumentResponse(BaseModel):
    """Response schema for document operations."""

    document_uuid: str = Field(..., description="Unique document identifier")
    status: DocumentStatus = Field(..., description="Document processing status")
    name: str = Field(..., description="Document name")
    url: str = Field(..., description="Document URL")
    summary: str | None = Field(
        None, description="Document summary (null until processing completes)"
    )
    data_progress: float = Field(
        ..., ge=0.0, le=1.0, description="Processing progress (0.0 to 1.0)"
    )
    created_at: datetime = Field(..., description="Document creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class SummarizeRequest(BaseModel):
    """Request schema for text summarization."""

    text: str = Field(
        ..., min_length=1, max_length=100000, description="Text to summarize"
    )
    model: str | None = Field(default="llama2", description="Ollama model to use")
    max_length: int | None = Field(
        default=500, ge=50, le=2000, description="Maximum summary length"
    )
    language: str | None = Field(default="en", description="Language for summarization")


class SummarizeResponse(BaseModel):
    """Response schema for text summarization."""

    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Response message")


class ExtractionRequest(BaseModel):
    """Request schema for content extraction."""

    url: HttpUrl = Field(..., description="URL to extract content from")
    include_links: bool = Field(default=True, description="Include links in extraction")
    include_images: bool = Field(default=False, description="Include image information")
    language: str | None = Field(default="en", description="Language for extraction")


class ExtractionResponse(BaseModel):
    """Response schema for content extraction."""

    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Response message")


class ProgressResponse(BaseModel):
    """Response schema for task progress."""

    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    progress: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")
    message: str = Field(..., description="Progress message")
    result: dict | None = Field(default=None, description="Task result if completed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TaskResult(BaseModel):
    """Schema for completed task results."""

    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    result: dict = Field(..., description="Task result data")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Task creation timestamp")
    completed_at: datetime = Field(..., description="Task completion timestamp")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )
    request_id: str | None = Field(
        default=None, description="Request identifier for tracking"
    )


class HealthCheck(BaseModel):
    """Schema for health check responses."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    services: dict = Field(
        default_factory=dict, description="Dependent services status"
    )
