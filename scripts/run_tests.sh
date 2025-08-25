#!/bin/bash

# Test runner script for the summarizer API

set -e

echo "🧪 Running Summarizer API Test Suite"
echo "====================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies if not present
echo "📋 Checking test dependencies..."
pip install pytest pytest-asyncio httpx pytest-cov > /dev/null 2>&1 || true

# Create logs directory for tests
mkdir -p logs

# Set test environment variables
export TESTING=true
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export REDIS_URL="redis://localhost:6379/15"
export LOG_LEVEL="DEBUG"

echo ""
echo "🏃‍♂️ Running test suite..."
echo ""

# Run different test categories
echo "🔧 Core API Tests:"
python -m pytest tests/test_api_core.py -v

echo ""
echo "📊 Progress Tracking Tests:"
python -m pytest tests/test_progress.py -v

echo ""
echo "🔍 Content Extraction Tests:"
python -m pytest tests/test_extraction.py -v

echo ""
echo "🔄 Uniqueness & Re-summarization Tests:"
python -m pytest tests/test_uniqueness_and_resummarize.py -v

echo ""
echo "⚡ Concurrency Tests:"
python -m pytest tests/test_concurrency.py -v

echo ""
echo "📝 Summarizer Tests:"
python -m pytest tests/test_summarizer_stub.py -v

echo ""
echo "🎯 Running full test suite with coverage:"
python -m pytest tests/ --cov=app --cov-report=term-missing

echo ""
echo "✅ All tests completed!"
echo ""
echo "📊 Coverage report generated in htmlcov/"
echo "🔍 To run specific tests:"
echo "   pytest tests/test_api_core.py::TestDocumentAPI::test_post_documents_returns_202_with_correct_shape -v"
echo ""
echo "🚀 To run only fast tests:"
echo "   pytest tests/ -m 'not slow' -v"
