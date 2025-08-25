"""Logging configuration for the application."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

from app.settings import get_settings

settings = get_settings()


def setup_logging(
    log_level: str = None, log_file: str = None, log_format: str = None
) -> None:
    """Setup logging configuration."""

    log_level = log_level or settings.log_level
    log_file = log_file or "logs/summarizer-api.log"
    log_format = log_format or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            # "json": {
            #     "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            #     "format": "%(timestamp)s %(level)s %(name)s %(message)s",
            # },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "default",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": log_file.replace(".log", "_error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "app": {  # Application logger
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {  # Uvicorn logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "fastapi": {  # FastAPI logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "sqlalchemy": {  # SQLAlchemy logger
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            },
            "httpx": {  # HTTPX logger
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            },
            "redis": {  # Redis logger
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            },
            "rq": {  # RQ logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    # Apply logging configuration
    logging.config.dictConfig(logging_config)

    # Set specific logger levels
    logging.getLogger("app").setLevel(log_level)

    # Log startup message
    logger = logging.getLogger("app")
    logger.info(f"Logging configured with level: {log_level}")
    logger.info(f"Log file: {log_file}")


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name is None:
        name = "app"
    return logging.getLogger(name)


class RequestLogger:
    """Logger for HTTP requests."""

    def __init__(self, name: str = "request"):
        self.logger = get_logger(name)

    def log_request(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time: float,
        user_agent: str = None,
        ip_address: str = None,
        request_id: str = None,
        **kwargs,
    ):
        """Log HTTP request details."""
        log_data = {
            "method": method,
            "url": url,
            "status_code": status_code,
            "response_time": response_time,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "request_id": request_id,
            **kwargs,
        }

        if status_code >= 400:
            self.logger.warning(f"Request failed: {log_data}")
        else:
            self.logger.info(f"Request completed: {log_data}")

    def log_error(
        self,
        method: str,
        url: str,
        error: Exception,
        user_agent: str = None,
        ip_address: str = None,
        request_id: str = None,
        **kwargs,
    ):
        """Log request errors."""
        log_data = {
            "method": method,
            "url": url,
            "error": str(error),
            "error_type": type(error).__name__,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "request_id": request_id,
            **kwargs,
        }

        self.logger.error(f"Request error: {log_data}")


class TaskLogger:
    """Logger for task operations."""

    def __init__(self, name: str = "task"):
        self.logger = get_logger(name)

    def log_task_created(
        self, task_id: str, task_type: str, input_data: dict[str, Any]
    ):
        """Log task creation."""
        self.logger.info(
            f"Task created: {task_id} ({task_type})",
            extra={
                "task_id": task_id,
                "task_type": task_type,
                "input_data": input_data,
            },
        )

    def log_task_started(self, task_id: str, task_type: str):
        """Log task start."""
        self.logger.info(
            f"Task started: {task_id} ({task_type})",
            extra={
                "task_id": task_id,
                "task_type": task_type,
            },
        )

    def log_task_completed(
        self, task_id: str, task_type: str, result: dict[str, Any] = None
    ):
        """Log task completion."""
        self.logger.info(
            f"Task completed: {task_id} ({task_type})",
            extra={
                "task_id": task_id,
                "task_type": task_type,
                "result": result,
            },
        )

    def log_task_failed(self, task_id: str, task_type: str, error: Exception):
        """Log task failure."""
        self.logger.error(
            f"Task failed: {task_id} ({task_type})",
            extra={
                "task_id": task_id,
                "task_type": task_type,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )


# Initialize logging when module is imported
if not logging.getLogger().handlers:
    setup_logging()
