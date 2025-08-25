# 🐳 Docker Guide for Summarizer API

Complete Docker setup and Docker Hub deployment guide for the Summarizer API project.

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

### **Local Development (Default)**
```bash
# Start all services (builds locally)
make up

# Initialize database
make db-migrate-docker

# Check health
make health
```

### **Docker Hub Deployment**
```bash
# Complete workflow: build, push, and deploy
./scripts/docker-hub.sh full -n yourusername

# Or use Makefile
make docker-hub-full DOCKER_NAMESPACE=yourusername
```

## 📦 Services

### **Core Services**

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| **api** | 8000 | FastAPI application | `/healthz` |
| **worker** | - | RQ background worker | Redis connection |
| **db** | 5432 | PostgreSQL database | `pg_isready` |
| **redis** | 6379 | Redis cache & queue | `redis-cli ping` |
| **ollama** | 11434 | LLM service (gemma3:1b) | `/api/tags` |

### **Optional Monitoring**

| Service | Port | Description | Credentials |
|---------|------|-------------|-------------|
| **prometheus** | 9090 | Metrics collection | - |
| **grafana** | 3000 | Metrics visualization | admin/admin |

## 🛠️ Available Commands

### **Basic Docker Operations**
```bash
make build          # Build all Docker images
make up             # Start all services
make down           # Stop all services
make restart        # Restart all services
make logs           # View logs from all services
```

### **With Monitoring**
```bash
make up-monitoring    # Start services + Prometheus + Grafana
make down-monitoring  # Stop all services including monitoring
```

### **Database Operations**
```bash
make db-migrate-docker  # Run database migrations
make db-reset-docker    # Reset database (⚠️ DATA LOSS)
```

### **API Utilities**
```bash
make openapi        # Generate OpenAPI specification
make test-docker    # Run tests in Docker
make pull-model     # Update Ollama model
```

## 🐳 Docker Hub Operations

### **Prerequisites**
1. **Docker Hub Account**: Create at [hub.docker.com](https://hub.docker.com)
2. **Login**: `docker login`
3. **Set namespace**: `export DOCKER_NAMESPACE=yourusername`

### **Available Commands**

#### **Using the Unified Script**
```bash
# Build images for Docker Hub
./scripts/docker-hub.sh build -n yourusername

# Push images to Docker Hub
./scripts/docker-hub.sh push -n yourusername

# Deploy from Docker Hub
./scripts/docker-hub.sh deploy -n yourusername

# Complete workflow
./scripts/docker-hub.sh full -n yourusername
```

#### **Using Makefile**
```bash
# Build images
make docker-hub-build DOCKER_NAMESPACE=yourusername

# Push images
make docker-hub-push DOCKER_NAMESPACE=yourusername

# Deploy
make docker-hub-deploy DOCKER_NAMESPACE=yourusername

# Complete workflow
make docker-hub-full DOCKER_NAMESPACE=yourusername
```

### **Configuration Options**

#### **Environment Variables**
```bash
# Required
export DOCKER_NAMESPACE=yourusername

# Optional
export VERSION=1.0.0

# For deployment from Docker Hub
export API_IMAGE=yourusername/api:latest
export WORKER_IMAGE=yourusername/worker:latest
export OLLAMA_IMAGE=yourusername/ollama:latest
```

#### **Script Options**
```bash
# Show help
./scripts/docker-hub.sh --help

# Custom version
./scripts/docker-hub.sh full -n yourusername -v 1.0.0

# With monitoring
./scripts/docker-hub.sh deploy -n yourusername -m
```

## 🏷️ Image Tagging Strategy

### **Tag Types**
- **`latest`** - Most recent version (always updated)
- **`{VERSION}`** - Semantic version from `pyproject.toml`
- **`{VERSION}-{REVISION}`** - Version with git commit hash

### **Example Tags**
```
yourusername/api:latest
yourusername/api:0.1.0
yourusername/api:0.1.0-a1b2c3d
```

## 📊 Image Specifications

| Component | Base Image | Size | Features |
|-----------|------------|------|----------|
| **API** | `python:3.12-slim` | ~856MB | FastAPI, dependencies, health checks |
| **Worker** | `python:3.12-slim` | ~856MB | RQ worker, dependencies, health checks |
| **Ollama** | `ollama/ollama:latest` | ~3.4GB | LLM runtime, gemma3:1b model |

## 🔒 Security Features

- **Non-root execution** in all containers
- **Health checks** for container orchestration
- **Resource limits** to prevent resource exhaustion
- **Network isolation** between services
- **SSRF protection** in content extraction
- **Input validation** and sanitization

## 📈 Monitoring & Observability

### **Built-in Monitoring**
- **Health checks** for all services
- **Structured logging** with request IDs
- **Prometheus metrics** for observability
- **Grafana dashboards** for visualization

### **Deployment Options**
```bash
# Basic deployment
./scripts/docker-hub.sh deploy -n yourusername

# With monitoring stack
./scripts/docker-hub.sh deploy -n yourusername -m
```

## 🔄 CI/CD Integration

### **GitHub Actions Example**
```yaml
name: Build and Push to Docker Hub

on:
  push:
    tags: ['v*']

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Build and push
        run: |
          export DOCKER_NAMESPACE=${{ secrets.DOCKERHUB_USERNAME }}
          export VERSION=${GITHUB_REF#refs/tags/}
          ./scripts/docker-hub.sh full -n ${{ secrets.DOCKERHUB_USERNAME }}
```

## 🎯 Usage Workflows

### **Development Workflow**
```bash
# 1. Start services locally
make up

# 2. Run migrations
make db-migrate-docker

# 3. Test API
curl http://localhost:8000/healthz
```

### **Docker Hub Publishing Workflow**
```bash
# 1. Login to Docker Hub
docker login

# 2. Set namespace
export DOCKER_NAMESPACE=yourusername

# 3. Build and push
./scripts/docker-hub.sh full -n yourusername
```

### **Production Deployment Workflow**
```bash
# 1. Set environment variables
export API_IMAGE=yourusername/api:latest
export WORKER_IMAGE=yourusername/worker:latest
export OLLAMA_IMAGE=yourusername/ollama:latest

# 2. Deploy
docker-compose up -d

# 3. Verify
make health
```

## 🚨 Troubleshooting

### **Common Issues**

#### **Authentication Errors**
```bash
# Re-login to Docker Hub
docker logout
docker login
```

#### **Permission Denied**
```bash
# Check Docker group membership
groups $USER

# Add to docker group (Linux)
sudo usermod -aG docker $USER
```

#### **Build Failures**
```bash
# Clean Docker cache
docker system prune -a

# Check Dockerfile syntax
docker build --no-cache -f Dockerfile.api .
```

### **Debug Commands**
```bash
# Check Docker Hub login
docker info | grep Username

# List local images
docker images | grep yourusername

# Validate compose file
docker-compose config

# Check service health
docker-compose ps
```

## 🎉 Success Metrics

### **What You Can Now Do**
✅ **Build production-ready Docker images**  
✅ **Push images to Docker Hub**  
✅ **Deploy from Docker Hub anywhere**  
✅ **Share images with your team**  
✅ **Integrate with CI/CD pipelines**  
✅ **Scale deployments easily**  
✅ **Monitor service health**  
✅ **Version and tag images**  

### **Benefits Achieved**
- **Professional image management** with proper tagging
- **Easy deployment** on any Docker-enabled system
- **Team collaboration** through shared images
- **CI/CD integration** for automated deployments
- **Production readiness** with health checks and monitoring
- **Version control** for image lifecycle management

## 📚 Quick Reference

### **Essential Commands**
```bash
# Development
make up                    # Start services locally
make health               # Check service health

# Docker Hub
./scripts/docker-hub.sh full -n yourusername  # Complete workflow
make docker-hub-full DOCKER_NAMESPACE=yourusername  # Via Makefile

# Deployment
docker-compose up -d      # Deploy (uses local or Docker Hub images)
```

### **Environment Variables**
```bash
# For Docker Hub operations
export DOCKER_NAMESPACE=yourusername
export VERSION=1.0.0

# For deployment from Docker Hub
export API_IMAGE=yourusername/api:latest
export WORKER_IMAGE=yourusername/worker:latest
export OLLAMA_IMAGE=yourusername/ollama:latest
```

---

**🎯 You now have a complete, professional Docker setup!**

The system provides both local development capabilities and Docker Hub deployment with a unified, simplified approach. You can easily share your images with others and deploy them anywhere Docker is available.
