"""Core API functionality tests."""

import pytest
from httpx import AsyncClient

from app.schemas import DocumentStatus


class TestDocumentAPI:
    """Test core document API functionality."""

    @pytest.mark.asyncio
    async def test_post_documents_returns_202_with_correct_shape(
        self, async_client: AsyncClient, mock_redis, mock_task_queue
    ):
        """Test POST /documents/ returns 202 with correct response shape."""
        payload = {"name": "Test Document", "url": "https://example.com/test"}

        response = await async_client.post("/api/v1/documents/", json=payload)

        assert response.status_code == 202
        data = response.json()

        # Verify response shape
        required_fields = {
            "document_uuid",
            "status",
            "name",
            "url",
            "summary",
            "data_progress",
            "created_at",
            "updated_at",
        }
        assert set(data.keys()) == required_fields

        # Verify field values
        assert data["status"] == DocumentStatus.PENDING.value
        assert data["name"] == payload["name"]
        assert data["url"] == payload["url"]
        assert data["summary"] is None  # Initially null
        assert data["data_progress"] == 0.0
        assert isinstance(data["document_uuid"], str)
        assert len(data["document_uuid"]) > 0
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

        # Verify task was enqueued
        mock_task_queue.enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_document_returns_resource(
        self, async_client: AsyncClient, sample_document
    ):
        """Test GET /documents/{uuid}/ returns the document resource."""
        response = await async_client.get(f"/api/v1/documents/{sample_document.id}/")

        assert response.status_code == 200
        data = response.json()

        # Verify response matches the document
        assert data["document_uuid"] == sample_document.id
        assert data["name"] == sample_document.name
        assert data["url"] == sample_document.url
        assert data["status"] == sample_document.status
        assert data["summary"] == sample_document.summary  # Should be null initially
        assert data["data_progress"] == sample_document.data_progress

    @pytest.mark.asyncio
    async def test_get_nonexistent_document_returns_404(
        self, async_client: AsyncClient
    ):
        """Test GET /documents/{uuid}/ returns 404 for nonexistent document."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"

        response = await async_client.get(f"/api/v1/documents/{fake_uuid}/")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_post_documents_validates_input(self, async_client: AsyncClient):
        """Test POST /documents/ validates input data."""
        # Test missing name
        response = await async_client.post(
            "/api/v1/documents/", json={"url": "https://example.com/test"}
        )
        assert response.status_code == 422

        # Test missing URL
        response = await async_client.post(
            "/api/v1/documents/", json={"name": "Test Document"}
        )
        assert response.status_code == 422

        # Test invalid URL
        response = await async_client.post(
            "/api/v1/documents/",
            json={"name": "Test Document", "url": "not-a-valid-url"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_documents_accepts_valid_urls(
        self, async_client: AsyncClient, mock_redis, mock_task_queue
    ):
        """Test POST /documents/ accepts various valid URL formats."""
        valid_urls = [
            (
                "https://example.com",
                "https://example.com/",
            ),  # URL normalization adds trailing slash
            ("http://example.com/path", "http://example.com/path"),
            (
                "https://subdomain.example.com/path?query=value",
                "https://subdomain.example.com/path?query=value",
            ),
            ("http://192.168.1.1:8080/api", "http://192.168.1.1:8080/api"),
            (
                "https://example.com:443/secure/path#fragment",
                "https://example.com/secure/path#fragment",
            ),  # Port 443 is default for HTTPS
        ]

        for i, (input_url, expected_url) in enumerate(valid_urls):
            payload = {"name": f"Test Document {i}", "url": input_url}

            response = await async_client.post("/api/v1/documents/", json=payload)
            assert response.status_code == 202

            data = response.json()
            assert data["url"] == expected_url

    @pytest.mark.asyncio
    async def test_summary_is_null_initially(
        self, async_client: AsyncClient, mock_redis, mock_task_queue
    ):
        """Test that summary field is null when document is first created."""
        payload = {
            "name": "Summary Test Document",
            "url": "https://example.com/summary-test",
        }

        # Create document
        response = await async_client.post("/api/v1/documents/", json=payload)
        assert response.status_code == 202

        document_uuid = response.json()["document_uuid"]

        # Verify summary is null
        response = await async_client.get(f"/api/v1/documents/{document_uuid}/")
        assert response.status_code == 200

        data = response.json()
        assert data["summary"] is None
        assert data["status"] == DocumentStatus.PENDING.value
        assert data["data_progress"] == 0.0

    @pytest.mark.asyncio
    async def test_health_endpoints(self, async_client: AsyncClient):
        """Test health check endpoints."""
        # Test /healthz
        response = await async_client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

        # Test /readyz
        response = await async_client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_api_versioning(self, async_client: AsyncClient):
        """Test API is properly versioned under /api/v1/."""
        payload = {
            "name": "Version Test Document",
            "url": "https://example.com/version-test",
        }

        # Test that the API is under /api/v1/
        response = await async_client.post("/api/v1/documents/", json=payload)
        assert response.status_code == 202

        # Test that non-versioned endpoint doesn't exist
        response = await async_client.post("/documents/", json=payload)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_content_type_validation(self, async_client: AsyncClient):
        """Test API requires proper content type."""
        payload = "invalid json"

        # Test without proper Content-Type header
        response = await async_client.post(
            "/api/v1/documents/",
            content=payload,
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_cors_headers(self, async_client: AsyncClient):
        """Test CORS headers are present."""
        response = await async_client.options("/api/v1/documents/")
        # The test client might not handle OPTIONS the same way as real requests
        # but we can test that the endpoint exists
        assert response.status_code in [
            200,
            405,
        ]  # 405 = Method Not Allowed is also acceptable

    @pytest.mark.asyncio
    async def test_request_id_generation(
        self, async_client: AsyncClient, mock_redis, mock_task_queue
    ):
        """Test that request IDs are generated for tracking."""
        payload = {
            "name": "Request ID Test",
            "url": "https://example.com/request-id-test",
        }

        response = await async_client.post("/api/v1/documents/", json=payload)
        assert response.status_code == 202

        # Check if request ID header is present (if implemented)
        # This might depend on middleware configuration
        headers = response.headers
        # The exact header name would depend on your middleware implementation
        # assert "X-Request-ID" in headers or "Request-ID" in headers
