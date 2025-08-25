"""Test configuration and fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_async_db
from app.main import app
from app.models import Document
from app.settings import Settings, get_settings

# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class TestSettings(Settings):
    """Test-specific settings."""

    database_url: str = TEST_DATABASE_URL
    redis_url: str = "redis://localhost:6379/15"  # Use different DB for tests
    log_level: str = "DEBUG"

    class Config:
        env_file = None  # Don't load .env in tests


@pytest.fixture
def test_settings() -> TestSettings:
    """Provide test settings."""
    return TestSettings()


@pytest_asyncio.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test database session."""
    async_session_factory = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture
def override_get_async_db(async_session):
    """Override database dependency for testing."""

    async def _get_async_db():
        yield async_session

    return _get_async_db


@pytest.fixture
def test_app(test_settings, override_get_async_db):
    """Create test FastAPI application."""
    # Override settings
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_async_db] = override_get_async_db

    yield app

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    from httpx import ASGITransport

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sync_client(test_app) -> TestClient:
    """Create synchronous test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.from_url.return_value = mock_redis

    with patch("app.tasks.redis_conn", mock_redis):
        with patch("app.redis_progress.redis_conn", mock_redis):
            yield mock_redis


@pytest.fixture
def mock_task_queue():
    """Mock RQ task queue."""
    mock_queue = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "test-job-id"
    mock_job.get_status.return_value = "queued"
    mock_queue.enqueue.return_value = mock_job

    with patch("app.tasks.task_queue", mock_queue):
        yield mock_queue


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client."""
    mock_client = AsyncMock()
    mock_client.summarize.return_value = "This is a test summary of the content."
    mock_client._trim_to_sentence_boundary.return_value = (
        "This is a test summary of the content."
    )

    with patch("app.tasks.ollama_client", mock_client):
        with patch("app.ollama_client.OllamaClient", return_value=mock_client):
            yield mock_client


@pytest.fixture
def mock_content_extractor():
    """Mock content extractor."""
    mock_extractor = AsyncMock()
    mock_extractor.extract_content_from_url.return_value = (
        "This is extracted content from the URL."
    )
    mock_extractor.clean_content.return_value = (
        "This is clean extracted content from the URL."
    )

    with patch("app.extraction.ContentExtractor") as mock_class:
        mock_class.return_value.__aenter__.return_value = mock_extractor
        mock_class.return_value.__aexit__.return_value = None
        yield mock_extractor


@pytest_asyncio.fixture
async def sample_document(async_session) -> Document:
    """Create a sample document for testing."""
    document = Document(
        name="Test Document",
        url="https://example.com/test",
        status="PENDING",
        data_progress=0.0,
    )
    async_session.add(document)
    await async_session.commit()
    await async_session.refresh(document)
    return document


# HTML fixtures for extraction testing
@pytest.fixture
def html_fixture_simple():
    """Simple HTML content fixture."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>This is the main content of the page.</p>
        <p>Another paragraph with some text.</p>
    </body>
    </html>
    """


@pytest.fixture
def html_fixture_complex():
    """Complex HTML content fixture."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complex Test Page</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <header>
            <nav>Navigation menu</nav>
        </header>
        <main>
            <article>
                <h1>Article Title</h1>
                <p>This is the main article content that should be extracted.</p>
                <p>Multiple paragraphs of meaningful content.</p>
                <section>
                    <h2>Section Header</h2>
                    <p>Section content with important information.</p>
                </section>
            </article>
        </main>
        <aside>
            <p>Sidebar content that might not be important.</p>
        </aside>
        <footer>
            <p>Footer information</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def html_fixture_minimal():
    """Minimal HTML that might result in empty extraction."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Empty</title></head>
    <body>
        <div id="ads">Advertisement</div>
        <nav>Navigation only</nav>
    </body>
    </html>
    """


# Content fixtures
@pytest.fixture
def long_text_content():
    """Long text content for testing summarization length limits."""
    return " ".join(
        [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit." * 50,
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua." * 50,
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco." * 50,
        ]
    )  # This will be > 1500 characters


@pytest.fixture
def short_text_content():
    """Short text content for testing."""
    return "This is a short piece of content for testing."


# Mock environment for subprocess isolation
@pytest.fixture
def isolated_env():
    """Isolated environment for testing."""
    with patch.dict(os.environ, {}, clear=True):
        yield
