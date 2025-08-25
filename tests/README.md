# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the Summarizer API with proper test isolation, mock services, and coverage for all advanced features.

## Test Structure

### 🏗️ Test Infrastructure (`conftest.py`)
- **Test App Setup**: Isolated FastAPI application with test database
- **Mock Services**: Redis, RQ, Ollama client, and content extractor mocks  
- **Test Database**: SQLite in-memory database for fast, isolated tests
- **Fixtures**: HTML content, sample documents, and test data

### 🔧 Core API Tests (`test_api_core.py`)
- ✅ **POST /documents/** returns 202 with correct shape
- ✅ **GET /documents/{uuid}/** returns resource data
- ✅ **Summary initially null** until processing completes
- ✅ **Input validation** for required fields and URL format
- ✅ **Health endpoints** (`/healthz`, `/readyz`)
- ✅ **API versioning** under `/api/v1/`

### 📊 Progress Tests (`test_progress.py`)
- ✅ **Pipeline stages**: `0.0 → 0.2 → 0.4 → 0.9 → 1.0`
- ✅ **Progress increases monotonically** through all stages
- ✅ **Failed stages preserve progress** at failure point
- ✅ **Idempotent processing** skips completed documents
- ✅ **Redis progress tracking** integration

### 🔍 Extraction Tests (`test_extraction.py`)
- ✅ **HTML fixtures**: Simple, complex, and minimal content
- ✅ **Content cleaning** with whitespace normalization
- ✅ **Error handling**: HTTP errors, network failures, timeouts
- ✅ **Security validation**: SSRF protection for private IPs and file URLs
- ✅ **Retry mechanism** with exponential backoff
- ✅ **Fallback to readability** when trafilatura fails

### 🔄 Uniqueness Tests (`test_uniqueness_and_resummarize.py`)
- ✅ **409 Conflict** for name collisions on different documents
- ✅ **409 Conflict** for URL collisions on different documents  
- ✅ **Exact name+URL match** re-triggers summarization
- ✅ **Re-summarization** clears previous state (summary, errors, progress)
- ✅ **Multiple resummarization cycles** support
- ✅ **Unicode and case sensitivity** handling

### ⚡ Concurrency Tests (`test_concurrency.py`)
- ✅ **Parallel POSTs** with same inputs create no duplicate rows
- ✅ **Queue management** prevents duplicate jobs
- ✅ **Race condition handling** in document creation
- ✅ **Database transaction isolation** under concurrent load
- ✅ **Mixed concurrent operations** (GET/POST combinations)
- ✅ **Memory stability** under high concurrent load

### 📝 Summarizer Tests (`test_summarizer_stub.py`)
- ✅ **≤1500 character enforcement** with automatic trimming
- ✅ **Sentence boundary trimming** preserves readability
- ✅ **Word boundary fallback** when no sentence endings found
- ✅ **Unicode character counting** accuracy
- ✅ **Quality requirements** (deterministic, no markdown, key facts)
- ✅ **Integration with pipeline** length validation

## Mock Services

### 🗄️ Database
```python
# SQLite in-memory for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
```

### 🔴 Redis
```python
# Mock Redis with basic operations
mock_redis.get.return_value = None
mock_redis.setex.return_value = True
```

### 🤖 Ollama Client
```python
# Mock summarization with length-controlled output
mock_client.summarize.return_value = "Test summary content."
```

### 🕷️ Content Extractor
```python
# Mock web content extraction
mock_extractor.extract_content_from_url.return_value = "Extracted content"
```

## Running Tests

### Quick Start
```bash
# Run all tests
./scripts/run_tests.sh

# Or manually
pytest tests/ -v
```

### Specific Test Categories
```bash
# Core API functionality
pytest tests/test_api_core.py -v

# Progress tracking
pytest tests/test_progress.py -v

# Content extraction  
pytest tests/test_extraction.py -v

# Uniqueness and re-summarization
pytest tests/test_uniqueness_and_resummarize.py -v

# Concurrency handling
pytest tests/test_concurrency.py -v

# Summarizer validation
pytest tests/test_summarizer_stub.py -v
```

### With Coverage
```bash
pytest tests/ --cov=app --cov-report=html
# View: htmlcov/index.html
```

## Test Fixtures

### HTML Content
- **Simple**: Basic HTML with clear content structure
- **Complex**: Real-world HTML with navigation, sidebars, etc.
- **Minimal**: Edge case HTML with little extractable content

### Test Data
- **Sample documents** with various states (PENDING, SUCCESS, FAILED)
- **Long text content** for testing summarization limits
- **Unicode content** for internationalization testing

## Integration Points

### Database Operations
- ✅ Document CRUD operations
- ✅ Status and progress updates  
- ✅ Unique constraint handling
- ✅ Transaction isolation

### External Services
- ✅ HTTP content fetching (mocked)
- ✅ Redis job queuing (mocked)
- ✅ Ollama summarization (mocked)
- ✅ Background task processing

### Business Logic
- ✅ Pipeline stage progression
- ✅ Error handling and recovery
- ✅ Idempotency enforcement
- ✅ Concurrent request handling

## Test Environment

### Configuration
```python
class TestSettings(Settings):
    database_url: str = "sqlite+aiosqlite:///:memory:"
    redis_url: str = "redis://localhost:6379/15" 
    log_level: str = "DEBUG"
```

### Dependencies
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `httpx` - HTTP client for API testing
- `pytest-cov` - Coverage reporting

## Coverage Goals

- **Overall Coverage**: ≥80%
- **Core API**: ≥95%
- **Business Logic**: ≥90%
- **Error Handling**: ≥85%

## Best Practices

### Test Isolation
- Each test uses fresh database
- Mocks reset between tests
- No shared state between tests

### Async Testing
```python
@pytest.mark.asyncio
async def test_async_operation():
    # Proper async test pattern
    result = await async_operation()
    assert result is not None
```

### Mock Usage
```python
# Comprehensive mocking
@pytest.fixture
def mock_service(mocker):
    return mocker.patch('app.service.external_call')
```

### Error Testing
```python
# Test both success and failure paths
with pytest.raises(ExpectedError):
    await operation_that_should_fail()
```

## Maintenance

### Adding New Tests
1. Follow existing patterns in test files
2. Use appropriate fixtures from `conftest.py`
3. Include both success and failure scenarios
4. Add concurrency tests for new endpoints

### Updating Mocks
1. Keep mocks in sync with real service interfaces
2. Update fixtures when data models change
3. Verify mock behavior matches real services

### Performance
- Tests should complete in <30 seconds total
- Individual tests should be <1 second
- Use `@pytest.mark.slow` for longer tests
