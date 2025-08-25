"""Main FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.errors import setup_error_handlers
from app.metrics import setup_metrics
from app.middleware import RequestIDMiddleware, RequestLoggingMiddleware
from app.settings import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Summarizer API",
        description="A FastAPI-based summarizer API with Ollama integration",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Setup metrics
    setup_metrics(app)

    # Setup error handlers
    setup_error_handlers(app)

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    @app.get("/healthz")
    async def healthz():
        """Health check endpoint for Kubernetes."""
        return {"status": "healthy"}

    @app.get("/readyz")
    async def readyz():
        """Readiness check endpoint for Kubernetes."""
        # Check if database is accessible
        try:
            from app.db import check_db_connection

            db_healthy = await check_db_connection()
            if not db_healthy:
                return {"status": "not ready", "reason": "database connection failed"}
        except Exception:
            return {"status": "not ready", "reason": "database check failed"}

        return {"status": "ready"}

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Summarizer API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
            "healthz": "/healthz",
            "readyz": "/readyz",
            "metrics": "/metrics",
        }

    @app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()


def main():
    """Run the application."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
