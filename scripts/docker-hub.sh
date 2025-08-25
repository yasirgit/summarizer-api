#!/bin/bash

# Unified Docker Hub Script for Summarizer API
# Handles building, pushing, and deploying in one place

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build     Build images for Docker Hub"
    echo "  push      Push images to Docker Hub"
    echo "  deploy    Deploy using Docker Hub images"
    echo "  full      Build, push, and deploy (complete workflow)"
    echo ""
    echo "Options:"
    echo "  -n, --namespace NAMESPACE  Docker Hub namespace (required)"
    echo "  -v, --version VERSION      Version tag (default: 0.1.0)"
    echo "  -m, --monitoring           Include monitoring stack"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  DOCKER_NAMESPACE           Docker Hub namespace"
    echo "  VERSION                    Version tag"
    echo ""
    echo "Examples:"
    echo "  $0 build -n myusername                    # Build images"
    echo "  $0 push -n myusername                     # Push images"
  echo "  $0 deploy -n myusername                   # Deploy from Docker Hub"
    echo "  $0 full -n myusername                     # Complete workflow"
    echo "  $0 full -n myusername -v 1.0.0 -m        # With version and monitoring"
    echo ""
    echo "Quick setup:"
    echo "  export DOCKER_NAMESPACE=myusername"
    echo "  $0 full"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "🔍 Checking prerequisites..."
    
    # Check Docker
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running or not accessible"
        exit 1
    fi
    print_success "Docker is running"
    
    # Check Docker Hub login
    if ! docker info | grep -q "Username"; then
        print_warning "Not logged into Docker Hub"
        print_status "Please run: docker login"
        read -p "Press Enter after logging in, or Ctrl+C to cancel..."
    else
        print_success "Logged into Docker Hub"
    fi
    
    # Check required files
    local required_files=("docker-compose.yml" "Dockerfile.api" "Dockerfile.worker" "Dockerfile.ollama")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            print_error "Required file not found: $file"
            exit 1
        fi
    done
    print_success "All required files found"
    
    echo
}

# Function to build images
build_images() {
    local namespace=$1
    local version=$2
    
    print_status "🏗️  Building images for Docker Hub..."
    print_status "Namespace: $namespace"
    print_status "Version: $version"
    echo
    
    # Set build arguments
    export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    export REVISION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    export VERSION=$version
    export DOCKER_NAMESPACE=$namespace
    
    # Build images
    docker-compose build --parallel
    print_success "Images built successfully!"
    echo
}

# Function to push images
push_images() {
    local namespace=$1
    local version=$2
    
    print_status "📤 Pushing images to Docker Hub..."
    print_status "Namespace: $namespace"
    print_status "Version: $version"
    echo
    
    # Tag and push images
    local images=("api" "worker" "ollama")
    
    for image in "${images[@]}"; do
        print_status "Pushing $image..."
        
        # Tag with multiple versions
        docker tag "summarizer-api_${image}:latest" "$namespace/$image:latest"
        docker tag "summarizer-api_${image}:latest" "$namespace/$image:$version"
        docker tag "summarizer-api_${image}:latest" "$namespace/$image:$version-$REVISION"
        
        # Push all tags
        docker push "$namespace/$image:latest"
        docker push "$namespace/$image:$version"
        docker push "$namespace/$image:$version-$REVISION"
        
        print_success "Pushed $image successfully!"
    done
    
    echo
}

# Function to deploy services
deploy_services() {
    local namespace=$1
    local version=$2
    local monitoring=$3
    
    print_status "🚀 Deploying services from Docker Hub..."
    print_status "Namespace: $namespace"
    print_status "Version: $version"
    print_status "Monitoring: $monitoring"
    echo
    
    # Set environment variables for Docker Hub images
    export API_IMAGE="$namespace/api:$version"
    export WORKER_IMAGE="$namespace/worker:$version"
    export OLLAMA_IMAGE="$namespace/ollama:$version"
    
    # Deploy the stack
    if [[ "$monitoring" == true ]]; then
        print_status "Starting services with monitoring..."
        docker-compose --profile monitoring up -d
    else
        print_status "Starting services..."
        docker-compose up -d
    fi
    
    print_success "Services deployed successfully!"
    echo
    
    # Wait for services to be ready
    print_status "⏳ Waiting for services to be ready..."
    sleep 15
    
    # Show service status
    print_status "📊 Service status:"
    docker-compose ps
    echo
    
    # Show service URLs
    print_success "Deployment completed!"
    echo
    print_status "🌐 Services available at:"
    echo "  📊 API:          http://localhost:8000"
    echo "  📖 API Docs:     http://localhost:8000/docs"
    echo "  🗄️  Database:     localhost:5432"
    echo "  📮 Redis:        localhost:6379"
    echo "  🤖 Ollama:       localhost:11434"
    
    if [[ "$monitoring" == true ]]; then
        echo "  📈 Prometheus:   http://localhost:9090"
        echo "  📊 Grafana:      http://localhost:3000 (admin/admin)"
    fi
    
    echo
    print_status "📚 Useful commands:"
    echo "  View logs:        docker-compose logs -f"
    echo "  Check health:     docker-compose ps"
    echo "  Stop services:    docker-compose down"
    echo "  Restart:          docker-compose restart"
}

# Function to run complete workflow
run_full_workflow() {
    local namespace=$1
    local version=$2
    local monitoring=$3
    
    print_status "🚀 Starting complete Docker Hub workflow..."
    echo
    
    # Step 1: Build
    build_images "$namespace" "$version"
    
    # Step 2: Push
    push_images "$namespace" "$version"
    
    # Step 3: Deploy
    deploy_services "$namespace" "$version" "$monitoring"
    
    # Show summary
    show_summary "$namespace" "$version"
}

# Function to show summary
show_summary() {
    local namespace=$1
    local version=$2
    
    print_success "🎉 Docker Hub workflow completed!"
    echo
    
    print_status "📋 Summary:"
    echo "  ✅ Namespace: $namespace"
    echo "  ✅ Version: $version"
    echo "  ✅ Images built: Yes"
    echo "  ✅ Images pushed: Yes"
    echo "  ✅ Services deployed: Yes"
    echo
    
    print_status "🔗 Docker Hub Images:"
    echo "  API:     $namespace/api:$version"
    echo "  Worker:  $namespace/worker:$version"
    echo "  Ollama:  $namespace/ollama:$version"
    echo
    
    print_status "🎯 Next steps:"
    echo "  • Update version: Edit pyproject.toml and run this script again"
    echo "  • Share images: Others can now pull your images from Docker Hub"
    echo "  • CI/CD: Use these images in your deployment pipelines"
}

# Main execution
main() {
    # Parse command line arguments
    COMMAND=""
    NAMESPACE=""
    VERSION="0.1.0"
    MONITORING=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            build|push|deploy|full)
                COMMAND="$1"
                shift
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -m|--monitoring)
                MONITORING=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check if command is provided
    if [[ -z "$COMMAND" ]]; then
        print_error "Command is required!"
        show_usage
        exit 1
    fi
    
    # Check if namespace is provided
    if [[ -z "$NAMESPACE" ]]; then
        if [[ -z "$DOCKER_NAMESPACE" ]]; then
            print_error "Docker Hub namespace is required!"
            echo "Use -n option or set DOCKER_NAMESPACE environment variable"
            show_usage
            exit 1
        else
            NAMESPACE="$DOCKER_NAMESPACE"
        fi
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Execute command
    case "$COMMAND" in
        build)
            build_images "$NAMESPACE" "$VERSION"
            ;;
        push)
            push_images "$NAMESPACE" "$VERSION"
            ;;
        deploy)
            deploy_services "$NAMESPACE" "$VERSION" "$MONITORING"
            ;;
        full)
            run_full_workflow "$NAMESPACE" "$VERSION" "$MONITORING"
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
