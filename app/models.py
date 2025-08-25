"""SQLAlchemy database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


class Document(Base):
    """Document model for tracking document processing."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING, FETCHING, PARSING, SUMMARIZING, SUCCESS, FAILED
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Additional metadata
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # in seconds
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, name={self.name}, status={self.status})>"


# Indexes for Document model
Index("ix_documents_status", Document.status)
Index("ix_documents_created_at", Document.created_at)


class Task(Base):
    """Task model for tracking summarization and extraction jobs."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'summarize' or 'extract'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed, failed
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Input data
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Output data
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additional data
    additional_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Performance metrics
    processing_time: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # in seconds
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self):
        return f"<Task(id={self.id}, type={self.task_type}, status={self.status})>"


class SummarizationTask(Base):
    """Specific model for summarization tasks."""

    __tablename__ = "summarization_tasks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="llama2")
    max_length: Mapped[int] = mapped_column(Float, nullable=False, default=500)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    word_count_original: Mapped[int | None] = mapped_column(Float, nullable=True)
    word_count_summary: Mapped[int | None] = mapped_column(Float, nullable=True)
    compression_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<SummarizationTask(id={self.id}, model={self.model})>"


class ExtractionTask(Base):
    """Specific model for content extraction tasks."""

    __tablename__ = "extraction_tasks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publish_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Extraction options
    include_links: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Extracted data
    links: Mapped[list | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extraction_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<ExtractionTask(id={self.id}, url={self.url})>"


class APIMetrics(Base):
    """Model for tracking API usage metrics."""

    __tablename__ = "api_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Float, nullable=False)
    response_time: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # in milliseconds
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self):
        return f"<APIMetrics(endpoint={self.endpoint}, status_code={self.status_code})>"
