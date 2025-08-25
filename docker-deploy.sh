#!/bin/bash
#
# Pwnagotchi Dashboard Docker Deployment Script
# Automated Docker deployment with configuration management
#
# Usage: ./docker-deploy.sh [--env=dev|prod] [--with-nginx] [--with-monitoring]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="pwnagotchi-dashboard"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Default values
ENVIRONMENT="prod"
WITH_NGINX=false
WITH_MONITORING=false
WITH_CACHE=false
FORCE_REBUILD=false
CLEANUP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env=*)
            ENVIRONMENT="${1#*=}"
            shift
            ;;
        --with-nginx)
            WITH_NGINX=true
            shift
            ;;
        --with-monitoring)
            WITH_MONITORING=true
            shift
            ;;
        --with-cache)
            WITH_CACHE=true
            shift
            ;;
        --rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --env=dev|prod        Environment (default: prod)"
            echo "  --with-nginx          Include nginx reverse proxy"
            echo "  --with-monitoring     Include Prometheus and Grafana"
            echo "  --with-cache          Include Redis cache"
            echo "  --rebuild             Force rebuild of images"
            echo "  --cleanup             Clean up containers and volumes"
            echo "  -h, --help            Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    local deps=("docker" "docker-compose")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing[*]}"
        echo "Please install:"
        echo "  Docker: https://docs.docker.com/get-docker/"
        echo "  Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    log_success "Dependencies check passed"
}

# Create environment file
create_env_file() {
    log_info "Creating environment file..."
    
    cat > "$ENV_FILE" << EOF
# Pwnagotchi Dashboard Environment Configuration
# Generated on $(date)

# Environment
ENVIRONMENT=$ENVIRONMENT
TZ=$(timedatectl show --property=Timezone --value 2>/dev/null || echo "UTC")

# Build information
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION=${VERSION:-latest}

# Security
SECRET_KEY=$(openssl rand -hex 32)
GRAFANA_PASSWORD=$(openssl rand -base64 12)

# Host configuration
HOST_USER_ID=$(id -u)
HOST_GROUP_ID=$(id -g)

# Database
POSTGRES_DB=pwnagotchi
POSTGRES_USER=pwnagotchi
POSTGRES_PASSWORD=$(openssl rand -base64 16)

# Redis
REDIS_PASSWORD=$(openssl rand -base64 16)
EOF
    
    log_success "Environment file created: $ENV_FILE"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    local dirs=(
        "config"
        "data"
        "logs"
        "ssl"
        "nginx/sites-available"
        "monitoring"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
    
    # Set permissions
    chmod 755 config data logs
    chmod 700 ssl
    
    log_success "Directory structure created"
}

# Create configuration files
create_configurations() {
    log_info "Creating configuration files..."
    
    # Main application config
    cat > "config/config.json" << EOF
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080,
    "debug": $([ "$ENVIRONMENT" == "dev" ] && echo "true" || echo "false")
  },
  "security": {
    "secret_key": "${SECRET_KEY:-$(openssl rand -hex 32)}",
    "rate_limit": {
      "per_day": $([ "$ENVIRONMENT" == "dev" ] && echo "2000" || echo "1000"),
      "per_hour": $([ "$ENVIRONMENT" == "dev" ] && echo "400" || echo "200"),
      "per_minute": $([ "$ENVIRONMENT" == "dev" ] && echo "60" || echo "30")
    }
  },
  "logging": {
    "level": "$([ "$ENVIRONMENT" == "dev" ] && echo "DEBUG" || echo "INFO")",
    "file": "/var/log/pwnagotchi/api.log",
    "max_size": "10MB",
    "backup_count": 5
  },
  "pwnagotchi": {
    "name": "pwnagotchi-docker",
    "scan_interval": 5,
    "auto_mode": true
  }
}
EOF
    
    # Nginx configuration
    if [[ "$WITH_NGINX" == true ]]; then
        cp nginx-pwnagotchi.conf nginx/sites-available/default.conf
        log_info "Nginx configuration created"
    fi
    
    # Monitoring configuration
    if [[ "$WITH_MONITORING" == true ]]; then
        cat > "monitoring/prometheus.yml" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'pwnagotchi-dashboard'
    static_configs:
      - targets: ['pwnagotchi-dashboard:8080']
    metrics_path: '/api/metrics'
    scrape_interval: 30s
EOF
        log_info "Monitoring configuration created"
    fi
    
    log_success "Configuration files created"
}

# Build profiles
build_profiles() {
    local profiles=()
    
    if [[ "$WITH_NGINX" == true ]]; then
        profiles+=("with-nginx")
    fi
    
    if [[ "$WITH_MONITORING" == true ]]; then
        profiles+=("with-monitoring")
    fi
    
    if [[ "$WITH_CACHE" == true ]]; then
        profiles+=("with-cache")
    fi
    
    echo "${profiles[@]}"
}

# Cleanup function
cleanup_deployment() {
    log_info "Cleaning up deployment..."
    
    # Stop and remove containers
    docker-compose down -v --remove-orphans 2>/dev/null || true
    
    # Remove images
    docker images "${PROJECT_NAME}*" -q | xargs -r docker rmi -f 2>/dev/null || true
    
    # Clean up volumes
    docker volume ls -q | grep "${PROJECT_NAME}" | xargs -r docker volume rm 2>/dev/null || true
    
    # Clean up networks
    docker network ls -q | grep "${PROJECT_NAME}" | xargs -r docker network rm 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Deploy function
deploy() {
    log_info "Starting deployment..."
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Build profiles
    local profiles=($(build_profiles))
    local profile_args=""
    
    if [[ ${#profiles[@]} -gt 0 ]]; then
        profile_args="--profile $(IFS=, ; echo "${profiles[*]// /,}")"
        log_info "Using profiles: ${profiles[*]}"
    fi
    
    # Build and start services
    if [[ "$FORCE_REBUILD" == true ]]; then
        log_info "Force rebuilding images..."
        eval "docker-compose $profile_args build --no-cache"
    fi
    
    log_info "Starting services..."
    eval "docker-compose $profile_args up -d"
    
    # Wait for health checks
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check service status
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker-compose ps | grep -q "healthy\|Up"; then
            log_success "Services are running"
            break
        fi
        
        ((attempt++))
        log_info "Waiting for services... ($attempt/$max_attempts)"
        sleep 10
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_error "Services failed to start properly"
        docker-compose logs --tail=50
        exit 1
    fi
}

# Show deployment info
show_deployment_info() {
    echo
    log_success "=== DEPLOYMENT COMPLETED ==="
    echo
    echo "Environment: $ENVIRONMENT"
    echo "Project: $PROJECT_NAME"
    echo
    echo "Services:"
    docker-compose ps
    echo
    echo "Access URLs:"
    
    if [[ "$WITH_NGINX" == true ]]; then
        echo "  Dashboard: http://localhost"
        echo "  API: http://localhost/api/status"
    else
        echo "  Dashboard: http://localhost:8080"
        echo "  API: http://localhost:8080/api/status"
    fi
    
    if [[ "$WITH_MONITORING" == true ]]; then
        echo "  Prometheus: http://localhost:9090"
        echo "  Grafana: http://localhost:3000 (admin/admin)"
    fi
    
    echo
    echo "Management Commands:"
    echo "  View logs:    docker-compose logs -f"
    echo "  Stop:         docker-compose down"
    echo "  Restart:      docker-compose restart"
    echo "  Update:       $0 --rebuild"
    echo "  Cleanup:      $0 --cleanup"
    echo
    echo "Configuration:"
    echo "  Config files: ./config/"
    echo "  Data export:  ./data/"
    echo "  Logs:         ./logs/"
    echo
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    local health_url="http://localhost:8080/api/status"
    if [[ "$WITH_NGINX" == true ]]; then
        health_url="http://localhost/api/status"
    fi
    
    if curl -f -s "$health_url" > /dev/null; then
        log_success "Health check passed"
        return 0
    else
        log_error "Health check failed"
        return 1
    fi
}

# Main function
main() {
    echo "========================================"
    echo "Pwnagotchi Dashboard Docker Deployment"
    echo "Environment: $ENVIRONMENT"
    echo "========================================"
    echo
    
    # Handle cleanup
    if [[ "$CLEANUP" == true ]]; then
        cleanup_deployment
        exit 0
    fi
    
    # Pre-deployment checks
    check_dependencies
    
    # Setup
    create_env_file
    create_directories
    create_configurations
    
    # Deploy
    deploy
    
    # Post-deployment
    sleep 5
    health_check
    show_deployment_info
    
    log_success "Deployment completed successfully!"
}

# Trap to cleanup on error
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"
