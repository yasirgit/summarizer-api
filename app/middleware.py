"""Custom middleware for request logging and other functionality."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.logging_conf import RequestLogger
from app.settings import get_settings

settings = get_settings()
request_logger = RequestLogger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Get client IP address
        client_ip = request.client.host if request.client else "unknown"

        # Get user agent
        user_agent = request.headers.get("user-agent", "unknown")

        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)

        # Process request
        try:
            response = await call_next(request)

            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Log successful request
            request_logger.log_request(
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                response_time=response_time,
                user_agent=user_agent,
                ip_address=client_ip,
                request_id=request_id,
            )

            return response

        except Exception as e:
            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Log request error
            request_logger.log_error(
                method=request.method,
                url=str(request.url),
                error=e,
                user_agent=user_agent,
                ip_address=client_ip,
                request_id=request_id,
            )

            raise


class CORSMiddleware:
    """Custom CORS middleware."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add CORS headers
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    headers = message.get("headers", [])
                    headers.extend(
                        [
                            (b"access-control-allow-origin", b"*"),
                            (
                                b"access-control-allow-methods",
                                b"GET, POST, PUT, DELETE, OPTIONS",
                            ),
                            (b"access-control-allow-headers", b"*"),
                        ]
                    )
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_cors)
        else:
            await self.app(scope, receive, send)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limit = settings.rate_limit_per_minute

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP for rate limiting
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit (simplified implementation)
        # In production, you'd use Redis or similar for distributed rate limiting
        if self._is_rate_limited(client_ip):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        # Process request
        response = await call_next(request)

        # Update rate limit counter
        self._update_rate_limit(client_ip)

        return response

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited."""
        # This is a simplified implementation
        # In production, use Redis with proper TTL
        return False

    def _update_rate_limit(self, client_ip: str):
        """Update rate limit counter for client."""
        # This is a simplified implementation
        # In production, use Redis with proper TTL
        pass


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware for adding request ID to all requests."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        import uuid

        request_id = str(uuid.uuid4())

        # Add request ID to request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for performance monitoring."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Add processing time to response headers
        response.headers["X-Processing-Time"] = str(processing_time)

        # Log slow requests
        if processing_time > 1000:  # Log requests taking more than 1 second
            request_logger.log_request(
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                response_time=processing_time,
                user_agent=request.headers.get("user-agent", "unknown"),
                ip_address=request.client.host if request.client else "unknown",
                slow_request=True,
            )

        return response


def setup_middleware(app):
    """Setup all middleware for the FastAPI application."""
    # Note: Some middleware is already added in main.py
    # This function can be used to add additional middleware if needed
    pass
