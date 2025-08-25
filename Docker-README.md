# 🐳 Docker Deployment Guide

Complete Docker setup for the Summarizer API with all services.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Service   │    │ Background      │
│   (Port 8000)   │◄──►│   (FastAPI)     │◄──►│ Worker (RQ)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                        ┌───────▼───────┐       ┌───────▼───────┐
                        │  PostgreSQL   │       │     Redis     │
                        │  (Port 5432)  │       │  (Port 6379)  │
                        └───────────────┘       └───────────────┘
                                │                       │
                        ┌───────▼───────────────────────▼───────┐
                        │           Ollama LLM Service          │
                        │           (Port 11434)                │
                        └───────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Build and Start Services
```bash
# Build all Docker images
make build

# Start all services
make up

# Check service health
make health
```

### 2. Initialize Database
```bash
# Run database migrations
make db-migrate-docker
```

### 3. Test the API
```bash
# Check API health
curl http://localhost:8000/healthz

# View API documentation
open http://localhost:8000/docs
```

## 📦 Services

### Core Services

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| **api** | 8000 | FastAPI application | `/healthz` |
| **worker** | - | RQ background worker | Redis connection |
| **db** | 5432 | PostgreSQL database | `pg_isready` |
| **redis** | 6379 | Redis cache & queue | `redis-cli ping` |
| **ollama** | 11434 | LLM service (gemma3:1b) | `/api/tags` |

### Optional Monitoring

| Service | Port | Description | Credentials |
|---------|------|-------------|-------------|
| **prometheus** | 9090 | Metrics collection | - |
| **grafana** | 3000 | Metrics visualization | admin/admin |

## 🛠️ Available Commands

### Docker Operations
```bash
make build          # Build all Docker images
make up             # Start all services
make down           # Stop all services
make restart        # Restart all services
make logs           # View logs from all services
```

### With Monitoring
```bash
make up-monitoring    # Start services + Prometheus + Grafana
make down-monitoring  # Stop all services including monitoring
```

### Database Operations
```bash
make db-migrate-docker  # Run database migrations
make db-reset-docker    # Reset database (⚠️ DATA LOSS)
```

### API Utilities
```bash
make openapi        # Generate OpenAPI specification
make test-docker    # Run tests in Docker
make pull-model     # Update Ollama model
```

### Health & Monitoring
```bash
make health         # Check all service health
make logs           # View service logs
```

### Cleanup
```bash
make clean-volumes  # Remove Docker volumes (⚠️ DATA LOSS)
make clean-all      # Remove all Docker resources
```

## 🔧 Configuration

### Environment Variables

Services are configured via environment variables in `docker-compose.yml`:

```yaml
# Database
DATABASE_URL: postgresql://user:password@db:5432/summarizer
POSTGRES_DB: summarizer
POSTGRES_USER: user
POSTGRES_PASSWORD: password

# Redis
REDIS_URL: redis://redis:6379/0

# Ollama
OLLAMA_BASE_URL: http://ollama:11434

# API
LOG_LEVEL: INFO
PYTHONPATH: /app
```

### Service Dependencies

Services start in order with health checks:
1. **db** (PostgreSQL)
2. **redis** 
3. **ollama** (with pre-pulled model)
4. **api** (depends on db, redis, ollama)
5. **worker** (depends on all above)

## 📊 Monitoring Setup

### Enable Monitoring
```bash
make up-monitoring
```

### Access Dashboards
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Custom Metrics
The API exposes Prometheus metrics at `/metrics`:
- Request rate and latency
- Error rates by endpoint
- Custom business metrics

## 🔍 Troubleshooting

### Check Service Status
```bash
docker-compose ps
```

### View Service Logs
```bash
# All services
make logs

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f ollama
```

### Test Individual Services

#### API Service
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/docs
```

#### Database
```bash
docker-compose exec db psql -U user -d summarizer -c "SELECT 1;"
```

#### Redis
```bash
docker-compose exec redis redis-cli ping
```

#### Ollama
```bash
curl http://localhost:11434/api/tags
```

### Common Issues

#### Ollama Model Not Ready
```bash
# Check model status
docker-compose exec ollama ollama list

# Pull model manually
make pull-model
```

#### Database Connection Issues
```bash
# Reset database
make db-reset-docker

# Check database logs
docker-compose logs db
```

#### Worker Not Processing Jobs
```bash
# Check worker logs
docker-compose logs worker

# Check Redis connection
docker-compose exec worker python -c "import redis; redis.from_url('redis://redis:6379/0').ping()"
```

## 🏗️ Development

### Local Development with Docker
```bash
# Start services
make up

# Run API locally (connects to Docker services)
make dev
```

### Testing
```bash
# Run tests in Docker
make test-docker

# Run tests locally
make test
```

### Database Migrations
```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
make db-migrate-docker
```

## 🔒 Security

### Production Considerations
1. **Change default passwords** in docker-compose.yml
2. **Use secrets management** for sensitive values
3. **Enable SSL/TLS** for external access
4. **Configure firewall rules** for service ports
5. **Use non-root users** (already configured)

### Network Security
- Services communicate on internal network `172.20.0.0/16`
- Only necessary ports are exposed to host
- Health checks ensure service integrity

## 📁 File Structure

```
summarizer-api/
├── Dockerfile.api              # API service image
├── Dockerfile.worker           # Worker service image  
├── Dockerfile.ollama           # Ollama with pre-pulled model
├── docker-compose.yml          # Service orchestration
├── scripts/
│   └── init-db.sql            # Database initialization
├── monitoring/
│   ├── prometheus.yml         # Prometheus configuration
│   └── grafana/               # Grafana dashboards & config
└── logs/                      # Shared log directory
```

## 🎯 API Endpoints

Once running, the API provides:

- **Health**: `GET /healthz`, `GET /readyz`
- **Documents**: `POST /api/v1/documents/`, `GET /api/v1/documents/{id}/`
- **Monitoring**: `GET /metrics` (Prometheus)
- **Documentation**: `GET /docs` (Swagger UI)

## 📈 Performance

### Resource Requirements
- **Minimum**: 4GB RAM, 2 CPU cores
- **Recommended**: 8GB RAM, 4 CPU cores
- **Storage**: ~2GB for images, ~1GB for models

### Scaling
- **API**: Scale with `docker-compose up --scale api=3`
- **Worker**: Scale with `docker-compose up --scale worker=2`
- **Database**: Consider external managed service for production

---

🎉 **Your Summarizer API is now running with Docker!**

Access the API at: http://localhost:8000/docs
