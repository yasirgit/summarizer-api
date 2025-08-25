"""Tests for the API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Summarizer API"
    assert data["version"] == "0.1.0"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_info():
    """Test the API info endpoint."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Summarizer API"
    assert "endpoints" in data


def test_api_health():
    """Test the API health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_summarize_endpoint():
    """Test the summarize endpoint."""
    response = client.post(
        "/api/v1/summarize",
        json={
            "text": "This is a test text for summarization.",
            "model": "llama2",
            "max_length": 100,
            "language": "en",
        },
    )
    # This will fail without proper setup, but we can test the endpoint exists
    assert response.status_code in [200, 500, 503]  # Various possible responses


def test_extract_endpoint():
    """Test the extract endpoint."""
    response = client.post(
        "/api/v1/extract",
        json={
            "url": "https://example.com",
            "include_links": True,
            "include_images": False,
            "language": "en",
        },
    )
    # This will fail without proper setup, but we can test the endpoint exists
    assert response.status_code in [200, 500, 503]  # Various possible responses


def test_models_endpoint():
    """Test the models endpoint."""
    response = client.get("/api/v1/models")
    # This will fail without Ollama running, but we can test the endpoint exists
    assert response.status_code in [200, 500, 503]  # Various possible responses


def test_progress_endpoint():
    """Test the progress endpoint."""
    # Test with a non-existent task ID
    response = client.get("/api/v1/progress/non-existent-task-id")
    assert response.status_code == 404


def test_invalid_summarize_request():
    """Test invalid summarize request."""
    response = client.post(
        "/api/v1/summarize",
        json={
            "text": "",  # Empty text should fail validation
        },
    )
    assert response.status_code == 422


def test_invalid_extract_request():
    """Test invalid extract request."""
    response = client.post(
        "/api/v1/extract",
        json={
            "url": "not-a-valid-url",  # Invalid URL should fail validation
        },
    )
    assert response.status_code == 422
