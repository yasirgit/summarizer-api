"""Error handling and normalization for the API."""

import traceback
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_conf import get_logger

logger = get_logger("errors")


class APIError(Exception):
    """Base API error class."""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        status_code: int = 500,
        details: dict[str, Any] = None,
        request_id: str = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error."""

    def __init__(
        self, message: str, details: dict[str, Any] = None, request_id: str = None
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
            request_id=request_id,
        )


class DocumentNotFoundError(APIError):
    """Document not found error."""

    def __init__(self, document_id: str, request_id: str = None):
        super().__init__(
            message=f"Document {document_id} not found",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=404,
            details={"document_id": document_id},
            request_id=request_id,
        )


class ProcessingError(APIError):
    """Document processing error."""

    def __init__(
        self, message: str, details: dict[str, Any] = None, request_id: str = None
    ):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            status_code=500,
            details=details,
            request_id=request_id,
        )


def normalize_error_response(
    error: Exception, request: Request, include_traceback: bool = False
) -> dict[str, Any]:
    """Normalize error response format."""
    request_id = getattr(request.state, "request_id", None)

    if isinstance(error, APIError):
        error_response = {
            "error": {
                "message": error.message,
                "code": error.error_code,
                "status_code": error.status_code,
                "request_id": error.request_id or request_id,
                "details": error.details,
            }
        }
    elif isinstance(error, HTTPException):
        error_response = {
            "error": {
                "message": error.detail,
                "code": f"HTTP_{error.status_code}",
                "status_code": error.status_code,
                "request_id": request_id,
                "details": {},
            }
        }
    elif isinstance(error, RequestValidationError):
        # Convert validation errors to JSON-serializable format
        validation_errors = []
        for err in error.errors():
            # Convert bytes to string representation for JSON serialization
            if "input" in err and isinstance(err["input"], bytes):
                err_copy = err.copy()
                err_copy["input"] = f"<bytes: {len(err['input'])} bytes>"
                validation_errors.append(err_copy)
            else:
                validation_errors.append(err)

        error_response = {
            "error": {
                "message": "Validation error",
                "code": "VALIDATION_ERROR",
                "status_code": 422,
                "request_id": request_id,
                "details": {"validation_errors": validation_errors},
            }
        }
    else:
        error_response = {
            "error": {
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
                "status_code": 500,
                "request_id": request_id,
                "details": {},
            }
        }

    if include_traceback:
        error_response["error"]["traceback"] = traceback.format_exc()

    return error_response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    error_response = normalize_error_response(exc, request)
    logger.error(f"HTTP Exception: {error_response}")

    return JSONResponse(status_code=exc.status_code, content=error_response)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation exceptions."""
    error_response = normalize_error_response(exc, request)
    logger.error(f"Validation Error: {error_response}")

    return JSONResponse(status_code=422, content=error_response)


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    error_response = normalize_error_response(exc, request)
    logger.error(f"General Exception: {error_response}", exc_info=True)

    return JSONResponse(status_code=500, content=error_response)


def setup_error_handlers(app):
    """Setup error handlers for the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
