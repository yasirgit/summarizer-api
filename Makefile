.PHONY: help install dev clean lint format test build up down logs restart
.PHONY: migrate db-create db-drop pull-model openapi validate-schema
.PHONY: up-monitoring down-monitoring test-docker health
.PHONY: setup quick-start docker-hub-build docker-hub-push docker-hub-deploy

# ============================================================================
# HELP & BASIC COMMANDS
# ============================================================================

help:  ## Show this help
	@echo "📋 Summarizer API - Available Commands"
	@echo "======================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make install  # Install dependencies"
	@echo "  make up       # Start all services"
	@echo "  make test     # Run tests"
	@echo ""
	@echo "🐳 Docker Hub Operations:"
	@echo "  make docker-hub-build  # Build images for Docker Hub"
	@echo "  make docker-hub-push   # Push images to Docker Hub"
	@echo "  make docker-hub-deploy # Deploy using Docker Hub images"
	@echo "  make docker-hub-full   # Complete workflow (build, push, deploy)"

# ============================================================================
# DEVELOPMENT SETUP
# ============================================================================

install:  ## Install dependencies
	@echo "📦 Installing dependencies..."
	pip install -e ".[dev]"
	@echo "✅ Installation complete!"

dev:  ## Run development server with hot reload
	@echo "🚀 Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

clean:  ## Clean up cache files and Docker resources
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/ .coverage htmlcov/ logs/ .ruff_cache/
	docker system prune -f
	@echo "✅ Cleanup complete!"

# ============================================================================
# CODE QUALITY
# ============================================================================

lint:  ## Run linting checks
	@echo "🔍 Running linting checks..."
	ruff check app/ tests/
	mypy app/ || true

format:  ## Format code and fix issues
	@echo "🎨 Formatting code..."
	ruff format app/ tests/
	ruff check --fix app/ tests/

test:  ## Run test suite with coverage
	@echo "🧪 Running tests..."
	pytest tests/ -v --cov=app --cov-report=term-missing

# ============================================================================
# DOCKER OPERATIONS
# ============================================================================

build:  ## Build all Docker images
	@echo "🏗️  Building Docker images..."
	docker-compose build --parallel
	@echo "✅ Build complete!"

up:  ## Start all services with Docker Compose
	@echo "🚀 Starting all services..."
	docker-compose up -d
	@echo ""
	@echo "🎉 Services are starting up!"
	@echo "📊 API: http://localhost:8000"
	@echo "📖 API Docs: http://localhost:8000/docs"
	@echo "🗄️  Database: localhost:5432"
	@echo "📮 Redis: localhost:6379" 
	@echo "🤖 Ollama: localhost:11434"
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@echo "   Run 'make health' to check status"

down:  ## Stop all services
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped!"

logs:  ## View logs from all services
	docker-compose logs -f

restart:  ## Restart all services
	@echo "🔄 Restarting services..."
	docker-compose restart
	@echo "✅ Services restarted!"

# ============================================================================
# DOCKER HUB OPERATIONS
# ============================================================================

docker-hub-build:  ## Build images for Docker Hub
	@echo "🏗️  Building Docker images for Docker Hub..."
	@echo "📝 Note: Set DOCKER_NAMESPACE and VERSION environment variables if needed"
	@echo "   Example: DOCKER_NAMESPACE=myusername VERSION=1.0.0 make docker-hub-build"
	./scripts/docker-hub.sh build -n $${DOCKER_NAMESPACE:-summarizer} -v $${VERSION:-0.1.0}

docker-hub-push:  ## Push images to Docker Hub
	@echo "📤 Pushing Docker images to Docker Hub..."
	@echo "📝 Note: Set DOCKER_NAMESPACE and VERSION environment variables if needed"
	@echo "   Example: DOCKER_NAMESPACE=myusername VERSION=1.0.0 make docker-hub-push"
	./scripts/docker-hub.sh push -n $${DOCKER_NAMESPACE:-summarizer} -v $${VERSION:-0.1.0}

docker-hub-deploy:  ## Deploy using Docker Hub images
	@echo "🚀 Deploying using Docker Hub images..."
	@echo "📝 Note: Set DOCKER_NAMESPACE and VERSION environment variables if needed"
	@echo "   Example: DOCKER_NAMESPACE=myusername VERSION=1.0.0 make docker-hub-deploy"
	@if [ -z "$$DOCKER_NAMESPACE" ]; then \
		echo "❌ Error: DOCKER_NAMESPACE environment variable is required"; \
		echo "   Example: DOCKER_NAMESPACE=myusername make docker-hub-deploy"; \
		exit 1; \
	fi
	./scripts/docker-hub.sh deploy -n $${DOCKER_NAMESPACE} -v $${VERSION:-0.1.0}

docker-hub-full:  ## Complete Docker Hub workflow (build, push, deploy)
	@echo "🚀 Running complete Docker Hub workflow..."
	@echo "📝 Note: Set DOCKER_NAMESPACE and VERSION environment variables if needed"
	@echo "   Example: DOCKER_NAMESPACE=myusername VERSION=1.0.0 make docker-hub-full"
	@if [ -z "$$DOCKER_NAMESPACE" ]; then \
		echo "❌ Error: DOCKER_NAMESPACE environment variable is required"; \
		echo "   Example: DOCKER_NAMESPACE=myusername make docker-hub-full"; \
		exit 1; \
	fi
	./scripts/docker-hub.sh full -n $${DOCKER_NAMESPACE} -v $${VERSION:-0.1.0}

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

migrate:  ## Run database migrations
	@echo "📊 Running database migrations..."
	alembic upgrade head
	@echo "✅ Migrations complete!"

db-create:  ## Create database tables
	@echo "🗄️  Creating database tables..."
	python -c "from app.db import create_tables; import asyncio; asyncio.run(create_tables())"
	@echo "✅ Tables created!"

db-drop:  ## Drop database tables (⚠️ DATA LOSS)
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		python -c "from app.db import drop_tables; import asyncio; asyncio.run(drop_tables())"; \
		echo "✅ Tables dropped!"; \
	else \
		echo "❌ Cancelled"; \
	fi

# ============================================================================
# LLM & API UTILITIES
# ============================================================================

pull-model:  ## Pull/update the Ollama model
	@echo "🤖 Pulling Ollama model (gemma3:1b)..."
	docker-compose exec ollama ollama pull gemma3:1b
	@echo "✅ Model updated!"

openapi:  ## Generate OpenAPI spec from running server
	@echo "📄 Exporting OpenAPI schema..."
	./scripts/export_openapi.sh

validate-schema:  ## Validate OpenAPI schema against requirements
	@echo "🔍 Validating OpenAPI schema..."
	python3 scripts/validate_schema.py

# ============================================================================
# MONITORING & OBSERVABILITY
# ============================================================================

up-monitoring:  ## Start services with monitoring (Prometheus + Grafana)
	@echo "🚀 Starting services with monitoring..."
	docker-compose --profile monitoring up -d
	@echo ""
	@echo "🎉 Services with monitoring are starting!"
	@echo "📊 API: http://localhost:8000"
	@echo "📈 Prometheus: http://localhost:9090"
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"

down-monitoring:  ## Stop services including monitoring
	@echo "🛑 Stopping services including monitoring..."
	docker-compose --profile monitoring down
	@echo "✅ All services stopped!"

# ============================================================================
# TESTING & VALIDATION
# ============================================================================

export-openapi:  ## Export OpenAPI spec from Docker
	docker-compose exec api python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json
	@echo "📄 OpenAPI spec generated: openapi.json"

test-docker:  ## Run tests in Docker
	docker-compose exec api pytest tests/ -v

# Health checks
health:  ## Check health of all services
	@echo "🏥 Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "🔍 API Health:"
	@curl -s http://localhost:8000/healthz | jq . || echo "❌ API not responding"
	@echo ""
	@echo "🔍 Ollama Health:"
	@curl -s http://localhost:11434/api/tags | jq . || echo "❌ Ollama not responding"

# Database utilities
db-migrate-docker:  ## Run migrations in Docker
	docker-compose exec api alembic upgrade head

db-reset-docker:  ## Reset database in Docker
	docker-compose exec api python -c "from app.db import drop_tables, create_tables; import asyncio; asyncio.run(drop_tables()); asyncio.run(create_tables())"

# Cleanup targets
clean-volumes:  ## Remove all Docker volumes (⚠️  DATA LOSS)
	@echo "⚠️  This will delete all data in Docker volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; echo; if [[ $$REPLY =~ ^[Yy]$$ ]]; then docker-compose down -v; fi

clean-all:  ## Remove containers, networks, volumes and images
	@echo "⚠️  This will delete all Docker resources for this project!"
	@read -p "Are you sure? [y/N] " -n 1 -r; echo; if [[ $$REPLY =~ ^[Yy]$$ ]]; then docker-compose down -v --rmi all; fi

# Legacy aliases for backward compatibility
docker-build: build  ## Alias for build
docker-up: up  ## Alias for up
docker-down: down  ## Alias for down
docker-logs: logs  ## Alias for logs

# Quick setup targets
setup: install build  ## Full setup for development
	@echo "Development environment setup complete!"
	@echo "Run 'make up' to start services"
	@echo "Run 'make dev' to start development server"

quick-start: up db-migrate-docker  ## Quick start with services and migrations
	@echo "Services started and database migrated!"
	@echo "API available at http://localhost:8000"