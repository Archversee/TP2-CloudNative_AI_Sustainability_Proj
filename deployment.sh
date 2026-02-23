#!/bin/bash

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' 

# Configuration
PROJECT_NAME="EcoEye"
NAMESPACE="ecoeye"
COMPOSE_FILE="infrastructure/docker/docker-compose.yaml"
K8S_DIR="infrastructure/kubernetes"

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing_tools=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    else
        print_success "Docker installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing_tools+=("docker-compose")
    else
        print_success "Docker Compose installed"
    fi
    
    # Check kubectl 
    if [ "$1" == "k8s" ]; then
        if ! command -v kubectl &> /dev/null; then
            missing_tools+=("kubectl")
        else
            print_success "kubectl installed"
        fi
    fi
    
    # Check .env file
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        echo ""
        echo "Please create a .env file in the project root with:"
        echo "  SUPABASE_URL=https://your-project.supabase.co"
        echo "  SUPABASE_ANON_KEY=your-anon-key"
        echo "  GEMINI_API_KEY=your-gemini-key"
        echo ""
        exit 1
    else
        print_success ".env file found"
    fi
    
    # Check if .env has required keys
    local required_keys=("SUPABASE_URL" "SUPABASE_ANON_KEY" "GEMINI_API_KEY")
    for key in "${required_keys[@]}"; do
        if ! grep -q "^${key}=" .env; then
            print_warning "Missing ${key} in .env file"
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    echo ""
}

rebuild_all_images() {
    print_header "Rebuilding All Docker Images for Kubernetes"
    
    build_kubernetes_images
    
    if [ $? -eq 0 ]; then
        echo ""
        print_success "All images rebuilt successfully!"
        print_info "To use in Kubernetes:"
        echo "  kubectl delete pods --all -n ecoeye"
    fi
}

rebuild_frontend() {
    print_header "Rebuilding Frontend for Kubernetes"
    
    local api_url="http://localhost:30800"
    
    print_info "Building frontend with API URL: $api_url"
    
    if docker build -t docker-frontend:latest \
        --build-arg NEXT_PUBLIC_API_URL=$api_url \
        -f services/frontend/Dockerfile \
        services/frontend; then
        
        print_success "Frontend rebuilt successfully!"
        
        # Check if deployed to K8s
        if kubectl get deployment frontend -n ecoeye &> /dev/null; then
            echo ""
            print_info "Frontend is deployed to Kubernetes"
            read -p "Restart frontend pod now? (y/n) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kubectl delete pod -l app=frontend -n ecoeye
                print_success "Frontend pod restarting with new image"
            else
                print_info "Run this to restart manually:"
                echo "  kubectl delete pod -l app=frontend -n ecoeye"
            fi
        fi
    else
        print_error "Frontend build failed!"
        return 1
    fi
}

deploy_docker_compose() {
    print_header "Deploying with Docker Compose"
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    # Navigate to docker directory
    cd infrastructure/docker || exit 1
    
    print_info "Building and starting containers..."
    docker-compose up --build -d
    
    if [ $? -eq 0 ]; then
        print_success "Docker Compose deployment successful!"
        echo ""
        print_info "Services are starting up..."
        sleep 5
        
        echo ""
        docker-compose ps
        
        echo ""
        print_success "Application is running!"
        print_info "Frontend: http://localhost:3000"
        print_info "API:      http://localhost:8000"
        print_info "API Docs: http://localhost:8000/docs"
        echo ""
        print_info "To view logs: docker-compose logs -f"
        print_info "To stop:      docker-compose down"
    else
        print_error "Docker Compose deployment failed!"
        exit 1
    fi
    
    cd ../.. || exit 1
}

stop_docker_compose() {
    print_header "Stopping Docker Compose"
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_warning "Docker Compose file not found: $COMPOSE_FILE"
        return
    fi
    
    cd infrastructure/docker || exit 1
    
    print_info "Stopping containers..."
    docker-compose down
    
    if [ "$1" == "cleanup" ]; then
        print_info "Removing volumes..."
        docker-compose down -v
        print_success "Cleanup complete!"
    else
        print_success "Containers stopped!"
    fi
    
    cd ../.. || exit 1
}

build_docker_images() {
    print_header "Building Docker Images for Docker Compose"
    
    print_info "Using Docker Compose for reliable builds..."
    
    # Check if compose file exists
    if [ ! -f "infrastructure/docker/docker-compose.yaml" ]; then
        print_error "Docker Compose file not found!"
        return 1
    fi
    
    cd infrastructure/docker || exit 1
    
    # Build with docker-compose
    if docker-compose build; then
        cd ../.. || exit 1
        print_success "All images built successfully!"
        echo ""
        docker images | grep -E "(docker-api|docker-frontend|docker-.*-worker)" | head -5
        echo ""
        return 0
    else
        cd ../.. || exit 1
        print_error "Docker Compose build failed!"
        return 1
    fi
}

build_kubernetes_images() {
    print_header "Building Docker Images for Kubernetes"
    
    print_info "Building images with Kubernetes-specific configuration..."
    
    # Build API (same for both)
    print_info "Building docker-api:latest..."
    if docker build -t docker-api:latest -f services/api/Dockerfile .; then
        print_success "docker-api:latest built successfully"
    else
        print_error "Failed to build docker-api:latest"
        return 1
    fi
    
    # Build Frontend with K8s API URL
    print_info "Building docker-frontend:latest (K8s version with NodePort URL)..."
    if docker build -t docker-frontend:latest \
        --build-arg NEXT_PUBLIC_API_URL=http://localhost:30800 \
        -f services/frontend/Dockerfile \
        services/frontend; then
        print_success "docker-frontend:latest built successfully"
    else
        print_error "Failed to build docker-frontend:latest"
        return 1
    fi
    
    # Build PDF Worker
    print_info "Building docker-pdf-worker:latest..."
    if docker build -t docker-pdf-worker:latest -f services/pdf-processor/Dockerfile .; then
        print_success "docker-pdf-worker:latest built successfully"
    else
        print_error "Failed to build docker-pdf-worker:latest"
        return 1
    fi
    
    # Build AI Worker
    print_info "Building docker-ai-worker:latest..."
    if docker build -t docker-ai-worker:latest -f services/ai-auditor/Dockerfile .; then
        print_success "docker-ai-worker:latest built successfully"
    else
        print_error "Failed to build docker-ai-worker:latest"
        return 1
    fi
    
    # Build Embeddings Worker
    print_info "Building docker-embeddings-worker:latest..."
    if docker build -t docker-embeddings-worker:latest -f services/embeddings/Dockerfile .; then
        print_success "docker-embeddings-worker:latest built successfully"
    else
        print_error "Failed to build docker-embeddings-worker:latest"
        return 1
    fi
    
    echo ""
    print_success "All Kubernetes images built successfully!"
    echo ""
    docker images | grep -E "(docker-api|docker-frontend|docker-.*-worker)" | head -5
    echo ""
}

deploy_kubernetes() {
    print_header "Deploying to Kubernetes"
    
    # Check if k8s directory exists
    if [ ! -d "$K8S_DIR" ]; then
        print_error "Kubernetes directory not found: $K8S_DIR"
        exit 1
    fi
    
    # Check if Kubernetes is running
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Kubernetes cluster is not accessible!"
        print_info "Make sure Docker Desktop Kubernetes is enabled:"
        print_info "  Settings → Kubernetes → Enable Kubernetes"
        exit 1
    fi
    
    print_success "Kubernetes cluster is accessible"
    
    # Check for --skip-build flag
    if [ "$SKIP_BUILD" = "true" ]; then
        print_warning "Skipping image build (--skip-build flag)"
        print_info "Using existing Docker images"
        
        # Verify images exist
        local required_images=("docker-api:latest" "docker-frontend:latest" "docker-pdf-worker:latest" "docker-ai-worker:latest" "docker-embeddings-worker:latest")
        for image in "${required_images[@]}"; do
            if ! docker image inspect "$image" &> /dev/null; then
                print_error "Image $image not found! Cannot skip build."
                print_info "Run without --skip-build flag to build images first"
                exit 1
            fi
        done
        print_success "All required images found"
    else
        # Check if images already exist
        local images_exist=true
        local required_images=("docker-api:latest" "docker-frontend:latest" "docker-pdf-worker:latest" "docker-ai-worker:latest" "docker-embeddings-worker:latest")
        
        print_info "Checking for existing Docker images..."
        for image in "${required_images[@]}"; do
            if docker image inspect "$image" &> /dev/null; then
                print_success "Found: $image"
            else
                print_warning "Missing: $image"
                images_exist=false
            fi
        done
        echo ""
        
        if [ "$images_exist" = true ]; then
            print_warning "Docker images exist, but may be built for Docker Compose"
            print_info "Rebuilding with Kubernetes configuration..."
            
            if ! build_kubernetes_images; then
                print_error "Image build failed!"
                exit 1
            fi
        else
            print_warning "Some images are missing, building for Kubernetes..."
            
            if ! build_kubernetes_images; then
                print_error "Image build failed!"
                exit 1
            fi
        fi
    fi
    
    # Create namespace
    print_info "Creating namespace..."
    kubectl apply -f "$K8S_DIR/namespace.yaml"
    print_success "Namespace created/updated"
    
    # Create or update secrets
    print_info "Creating secrets..."
    if kubectl get secret ecoeye-secrets -n $NAMESPACE &> /dev/null; then
        print_warning "Secret already exists, deleting..."
        kubectl delete secret ecoeye-secrets -n $NAMESPACE
    fi
    
    kubectl create secret generic ecoeye-secrets \
        --from-env-file=.env \
        --namespace=$NAMESPACE
    
    if [ $? -eq 0 ]; then
        print_success "Secrets created"
    else
        print_error "Failed to create secrets"
        exit 1
    fi
    
    # Deploy all resources
    print_info "Deploying resources..."
    kubectl apply -f "$K8S_DIR/"
    
    if [ $? -eq 0 ]; then
        print_success "Resources deployed"
    else
        print_error "Deployment failed"
        exit 1
    fi
    
    # Wait for pods to be ready
    print_info "Waiting for pods to be ready (this may take 1-2 minutes)..."
    echo ""
    
    # Show pod status
    kubectl get pods -n $NAMESPACE
    
    echo ""
    print_info "Waiting for all pods to be Running..."
    
    # Wait for all pods to be ready
    local timeout=180
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        local not_ready=$(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | grep -v "Running" | wc -l)
        
        if [ "$not_ready" -eq 0 ]; then
            break
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    echo ""
    
    # Final status check
    kubectl get pods -n $NAMESPACE
    echo ""
    
    local failed=$(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | grep -E "Error|CrashLoopBackOff|ImagePullBackOff" | wc -l)
    
    if [ "$failed" -gt 0 ]; then
        print_error "Some pods failed to start!"
        print_info "Check logs with: kubectl logs <pod-name> -n $NAMESPACE"
        exit 1
    fi
    
    print_success "All pods are running!"
    
    # Show services
    echo ""
    print_info "Services:"
    kubectl get svc -n $NAMESPACE
    
    echo ""
    print_success "Kubernetes deployment successful!"
    echo ""
    print_success "Access your application (NodePort):"
    print_info "  Frontend: http://localhost:30300"
    print_info "  API:      http://localhost:30800"
    print_info "  API Docs: http://localhost:30800/docs"
    echo ""
    print_info "Useful commands:"
    echo "  kubectl get pods -n $NAMESPACE           # View pods"
    echo "  kubectl logs -f <pod-name> -n $NAMESPACE # View logs"
    echo "  kubectl describe pod <pod-name> -n $NAMESPACE  # Debug pod"
    echo ""
}

stop_kubernetes() {
    print_header "Stopping Kubernetes Deployment"
    
    if [ "$1" == "cleanup" ]; then
        print_info "Deleting namespace (this removes everything)..."
        kubectl delete namespace $NAMESPACE
        print_success "Namespace deleted!"
    else
        print_info "Deleting resources..."
        kubectl delete -f "$K8S_DIR/" 2>/dev/null || true
        print_success "Resources deleted!"
        print_info "Namespace '$NAMESPACE' still exists (secrets preserved)"
        print_info "To completely remove: ./deployment.sh stop k8s --cleanup"
    fi
}

show_usage() {
    echo "Usage: $0 {start|stop|restart|rebuild|logs|status} {compose|k8s|all|frontend} [--cleanup|--skip-build]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the application"
    echo "  stop     - Stop the application"
    echo "  restart  - Restart the application"
    echo "  rebuild  - Rebuild Docker images"
    echo "  logs     - Show logs"
    echo "  status   - Show status"
    echo ""
    echo "Modes:"
    echo "  compose   - Docker Compose"
    echo "  k8s       - Kubernetes"
    echo "  all       - Rebuild all images (for rebuild command)"
    echo "  frontend  - Rebuild frontend only (for rebuild command)"
    echo ""
    echo "Flags:"
    echo "  --cleanup     - Remove volumes/namespace when stopping"
    echo "  --skip-build  - Skip image building (use existing images)"
    echo ""
    echo "Examples:"
    echo "  $0 start compose              # Start with Docker Compose"
    echo "  $0 start k8s                  # Start with Kubernetes (rebuilds images)"
    echo "  $0 start k8s --skip-build     # Start K8s without rebuilding"
    echo "  $0 rebuild all                # Rebuild all 5 images for K8s"
    echo "  $0 rebuild frontend           # Rebuild frontend only for K8s"
    echo "  $0 stop k8s --cleanup         # Stop K8s and delete namespace"
    echo ""
}

show_logs() {
    if [ "$1" == "compose" ]; then
        cd infrastructure/docker || exit 1
        docker-compose logs -f
        cd ../.. || exit 1
    else
        print_info "Available pods:"
        kubectl get pods -n $NAMESPACE
        echo ""
        print_info "To view logs: kubectl logs -f <pod-name> -n $NAMESPACE"
    fi
}

show_status() {
    if [ "$1" == "compose" ]; then
        print_header "Docker Compose Status"
        cd infrastructure/docker || exit 1
        docker-compose ps
        cd ../.. || exit 1
    else
        print_header "Kubernetes Status"
        echo ""
        print_info "Pods:"
        kubectl get pods -n $NAMESPACE
        echo ""
        print_info "Services:"
        kubectl get svc -n $NAMESPACE
        echo ""
        print_info "Secrets:"
        kubectl get secrets -n $NAMESPACE
    fi
}

# Main script
main() {
    local command=$1
    local mode=$2
    local flag=$3
    
    # Initialize global flags
    SKIP_BUILD=false
    
    # Check for --skip-build flag
    if [ "$flag" == "--skip-build" ]; then
        SKIP_BUILD=true
    fi
    
    # Check if no arguments
    if [ -z "$command" ] || [ -z "$mode" ]; then
        show_usage
        exit 1
    fi
    
    # Validate mode based on command
    if [ "$command" == "rebuild" ]; then
        # Rebuild command uses 'all' or 'frontend'
        if [ "$mode" != "all" ] && [ "$mode" != "frontend" ]; then
            print_error "Invalid rebuild mode: $mode"
            print_info "Use: rebuild all OR rebuild frontend"
            show_usage
            exit 1
        fi
    else
        # Other commands use 'compose' or 'k8s'
        if [ "$mode" != "compose" ] && [ "$mode" != "k8s" ]; then
            print_error "Invalid mode: $mode"
            show_usage
            exit 1
        fi
    fi
    
    # Check prerequisites 
    if [ "$command" != "stop" ] && [ "$command" != "rebuild" ]; then
        check_prerequisites "$mode"
    fi
    
    # Execute command
    case $command in
        start)
            if [ "$mode" == "compose" ]; then
                deploy_docker_compose
            else
                deploy_kubernetes
            fi
            ;;
        stop)
            if [ "$mode" == "compose" ]; then
                stop_docker_compose "$flag"
            else
                stop_kubernetes "$flag"
            fi
            ;;
        restart)
            if [ "$mode" == "compose" ]; then
                stop_docker_compose
                deploy_docker_compose
            else
                stop_kubernetes
                deploy_kubernetes
            fi
            ;;
        rebuild)
            if [ "$mode" == "all" ]; then
                rebuild_all_images
            elif [ "$mode" == "frontend" ]; then
                rebuild_frontend
            fi
            ;;
        logs)
            show_logs "$mode"
            ;;
        status)
            show_status "$mode"
            ;;
        *)
            print_error "Invalid command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"