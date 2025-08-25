"""Metrics and monitoring functionality using Prometheus."""

from typing import Any

from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_fastapi_instrumentator import Instrumentator, metrics

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

ACTIVE_REQUESTS = Gauge(
    "http_active_requests", "Number of active HTTP requests", ["method", "endpoint"]
)

TASK_COUNT = Counter("tasks_total", "Total number of tasks", ["type", "status"])

TASK_DURATION = Histogram(
    "task_duration_seconds", "Task duration in seconds", ["type", "status"]
)

ACTIVE_TASKS = Gauge("active_tasks", "Number of active tasks", ["type"])

OLLAMA_REQUESTS = Counter(
    "ollama_requests_total", "Total number of Ollama API requests", ["model", "status"]
)

OLLAMA_REQUEST_DURATION = Histogram(
    "ollama_request_duration_seconds",
    "Ollama API request duration in seconds",
    ["model"],
)

EXTRACTION_REQUESTS = Counter(
    "extraction_requests_total",
    "Total number of content extraction requests",
    ["status"],
)

EXTRACTION_DURATION = Histogram(
    "extraction_duration_seconds", "Content extraction duration in seconds"
)

# Application info
APP_INFO = Info("summarizer_api", "Summarizer API information")


def setup_metrics(app: FastAPI) -> None:
    """Setup Prometheus metrics for the FastAPI application."""

    # Set application info
    APP_INFO.info(
        {
            "version": "0.1.0",
            "name": "Summarizer API",
            "description": "A FastAPI-based summarizer API with Ollama integration",
        }
    )

    # Setup instrumentator with custom metrics
    instrumentator = Instrumentator(
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health"],
        env_var_name="ENABLE_METRICS",
    )

    # Add custom metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    instrumentator.add(
        metrics.latency(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    # Instrument the application
    instrumentator.instrument(app).expose(app, include_in_schema=True, should_gzip=True)


def record_request_metrics(
    method: str, endpoint: str, status: int, duration: float
) -> None:
    """Record HTTP request metrics."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def record_task_metrics(task_type: str, status: str, duration: float = None) -> None:
    """Record task metrics."""
    TASK_COUNT.labels(type=task_type, status=status).inc()

    if duration is not None:
        TASK_DURATION.labels(type=task_type, status=status).observe(duration)


def set_active_tasks(task_type: str, count: int) -> None:
    """Set the number of active tasks."""
    ACTIVE_TASKS.labels(type=task_type).set(count)


def record_ollama_metrics(model: str, status: str, duration: float = None) -> None:
    """Record Ollama API metrics."""
    OLLAMA_REQUESTS.labels(model=model, status=status).inc()

    if duration is not None:
        OLLAMA_REQUEST_DURATION.labels(model=model).observe(duration)


def record_extraction_metrics(status: str, duration: float = None) -> None:
    """Record content extraction metrics."""
    EXTRACTION_REQUESTS.labels(status=status).inc()

    if duration is not None:
        EXTRACTION_DURATION.observe(duration)


class MetricsCollector:
    """Collector for custom application metrics."""

    def __init__(self):
        self.metrics = {}

    def record_custom_metric(
        self, name: str, value: float, labels: dict[str, str] = None
    ) -> None:
        """Record a custom metric."""
        if name not in self.metrics:
            self.metrics[name] = {}

        label_key = str(labels) if labels else "default"
        self.metrics[name][label_key] = value

    def get_custom_metrics(self) -> dict[str, Any]:
        """Get all custom metrics."""
        return self.metrics.copy()

    def clear_custom_metrics(self) -> None:
        """Clear all custom metrics."""
        self.metrics.clear()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_summary() -> dict[str, Any]:
    """Get a summary of all metrics."""
    return {
        "http_requests": {
            "total": REQUEST_COUNT._value.sum(),
            "duration_avg": REQUEST_DURATION.observe(0),  # This is a placeholder
        },
        "tasks": {
            "total": TASK_COUNT._value.sum(),
            "active": ACTIVE_TASKS._value.sum(),
        },
        "ollama": {
            "total_requests": OLLAMA_REQUESTS._value.sum(),
        },
        "extraction": {
            "total_requests": EXTRACTION_REQUESTS._value.sum(),
        },
        "custom_metrics": metrics_collector.get_custom_metrics(),
    }


def reset_metrics() -> None:
    """Reset all metrics (useful for testing)."""
    # Reset Prometheus metrics
    REQUEST_COUNT._value.clear()
    REQUEST_DURATION._value.clear()
    ACTIVE_REQUESTS._value.clear()
    TASK_COUNT._value.clear()
    TASK_DURATION._value.clear()
    ACTIVE_TASKS._value.clear()
    OLLAMA_REQUESTS._value.clear()
    OLLAMA_REQUEST_DURATION._value.clear()
    EXTRACTION_REQUESTS._value.clear()
    EXTRACTION_DURATION._value.clear()

    # Clear custom metrics
    metrics_collector.clear_custom_metrics()
