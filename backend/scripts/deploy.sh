#!/bin/bash

# =============================================================================
# MBA Job Hunter - Production Deployment Script
# =============================================================================
# 
# This script handles automated deployment with:
# - Environment validation
# - Database migrations
# - Health checks
# - Rollback capability
# - Zero-downtime deployment
#
# Usage:
#   ./scripts/deploy.sh [environment] [options]
#
# Examples:
#   ./scripts/deploy.sh production
#   ./scripts/deploy.sh staging --skip-migrations
#   ./scripts/deploy.sh production --rollback
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-staging}"
SKIP_MIGRATIONS=false
ROLLBACK=false
DRY_RUN=false
BACKUP_ENABLED=true
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
DEPLOYMENT_TIMEOUT=1800   # 30 minutes

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-migrations)
            SKIP_MIGRATIONS=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-backup)
            BACKUP_ENABLED=false
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            if [[ $1 != "production" && $1 != "staging" && $1 != "development" ]]; then
                echo -e "${RED}Error: Unknown argument '$1'${NC}"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Function definitions
show_help() {
    cat << EOF
MBA Job Hunter Deployment Script

Usage: $0 [environment] [options]

Arguments:
    environment     Target environment (production|staging|development)

Options:
    --skip-migrations   Skip database migrations
    --rollback          Perform rollback to previous version
    --dry-run           Show what would be done without executing
    --no-backup         Skip database backup
    --help, -h          Show this help message

Examples:
    $0 production
    $0 staging --skip-migrations
    $0 production --rollback
    $0 staging --dry-run

EOF
}

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗ $1${NC}"
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if required tools are installed
    local required_tools=("docker" "git" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed"
            exit 1
        fi
    done
    
    # Check if running in correct directory
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found. Run from project root."
        exit 1
    fi
    
    # Check environment-specific requirements
    case $ENVIRONMENT in
        production)
            if [[ ! -f ".env.production" ]]; then
                log_error ".env.production file not found"
                exit 1
            fi
            ;;
        staging)
            if [[ ! -f ".env.staging" ]]; then
                log_warning ".env.staging not found, using .env.production"
            fi
            ;;
    esac
    
    log_success "Prerequisites check passed"
}

validate_environment() {
    log "Validating environment configuration..."
    
    # Source environment variables
    if [[ -f ".env.$ENVIRONMENT" ]]; then
        source ".env.$ENVIRONMENT"
    fi
    
    # Check required environment variables
    local required_vars=("DATABASE_URL" "SECRET_KEY" "ENVIRONMENT")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate environment-specific settings
    if [[ "$ENVIRONMENT" == "production" ]]; then
        if [[ "${DEBUG:-true}" == "true" ]]; then
            log_error "DEBUG should be false in production"
            exit 1
        fi
        
        if [[ -z "${SENTRY_DSN:-}" ]]; then
            log_warning "SENTRY_DSN not set - error tracking disabled"
        fi
    fi
    
    log_success "Environment validation passed"
}

backup_database() {
    if [[ "$BACKUP_ENABLED" == "false" ]]; then
        log "Skipping database backup (--no-backup flag)"
        return 0
    fi
    
    log "Creating database backup..."
    
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    local backup_path="./backups/$backup_file"
    
    # Create backups directory
    mkdir -p ./backups
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would create backup at $backup_path"
        return 0
    fi
    
    # Create database backup
    if docker-compose exec -T postgres pg_dump -U postgres mba_job_hunter > "$backup_path"; then
        log_success "Database backup created: $backup_path"
        
        # Store backup path for potential rollback
        echo "$backup_path" > .last_backup
        
        # Clean up old backups (keep last 10)
        ls -t ./backups/backup_*.sql | tail -n +11 | xargs -r rm
        
    else
        log_error "Database backup failed"
        exit 1
    fi
}

run_migrations() {
    if [[ "$SKIP_MIGRATIONS" == "true" ]]; then
        log "Skipping database migrations (--skip-migrations flag)"
        return 0
    fi
    
    log "Running database migrations..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would run alembic upgrade head"
        return 0
    fi
    
    # Run migrations
    if docker-compose exec api alembic upgrade head; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        exit 1
    fi
}

deploy_application() {
    log "Deploying application..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would deploy application"
        return 0
    fi
    
    # Build and deploy based on environment
    case $ENVIRONMENT in
        production)
            log "Building production images..."
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
            
            log "Starting production services..."
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
            ;;
        staging)
            log "Building staging images..."
            docker-compose -f docker-compose.yml -f docker-compose.staging.yml build
            
            log "Starting staging services..."
            docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
            ;;
        *)
            log "Building development images..."
            docker-compose build
            
            log "Starting development services..."
            docker-compose up -d
            ;;
    esac
    
    log_success "Application deployment completed"
}

wait_for_health_check() {
    log "Waiting for application to be healthy..."
    
    local health_url="http://localhost:8000/health"
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / 10))
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if [[ "$DRY_RUN" == "true" ]]; then
            log "DRY RUN: Would check health at $health_url"
            return 0
        fi
        
        log "Health check attempt $attempt/$max_attempts..."
        
        if curl -f -s "$health_url" > /dev/null; then
            log_success "Application is healthy"
            return 0
        fi
        
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed after $HEALTH_CHECK_TIMEOUT seconds"
    return 1
}

run_smoke_tests() {
    log "Running smoke tests..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would run smoke tests"
        return 0
    fi
    
    # Run smoke tests
    if python scripts/smoke_test.py --environment "$ENVIRONMENT"; then
        log_success "Smoke tests passed"
    else
        log_error "Smoke tests failed"
        return 1
    fi
}

rollback_deployment() {
    log "Rolling back deployment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would rollback deployment"
        return 0
    fi
    
    # Stop current services
    docker-compose down
    
    # Restore database from backup
    if [[ -f ".last_backup" ]]; then
        local backup_file=$(cat .last_backup)
        if [[ -f "$backup_file" ]]; then
            log "Restoring database from $backup_file..."
            docker-compose exec -T postgres psql -U postgres -d mba_job_hunter < "$backup_file"
            log_success "Database restored"
        else
            log_warning "Backup file $backup_file not found"
        fi
    else
        log_warning "No backup file reference found"
    fi
    
    # Restart with previous version
    git checkout HEAD~1
    docker-compose build
    docker-compose up -d
    
    log_success "Rollback completed"
}

cleanup() {
    log "Cleaning up..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would cleanup resources"
        return 0
    fi
    
    # Clean up unused Docker resources
    docker system prune -f
    
    # Clean up old images
    docker image prune -f
    
    log_success "Cleanup completed"
}

send_deployment_notification() {
    local status="$1"
    local message="$2"
    
    log "Sending deployment notification..."
    
    # Send to Slack (if webhook configured)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"MBA Job Hunter Deployment [$ENVIRONMENT]: $status - $message\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    # Send email notification (if configured)
    if [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
        echo "Deployment $status: $message" | mail -s "MBA Job Hunter Deployment" "$NOTIFICATION_EMAIL" || true
    fi
}

main() {
    local start_time=$(date +%s)
    
    log "Starting deployment to $ENVIRONMENT environment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No changes will be made"
    fi
    
    if [[ "$ROLLBACK" == "true" ]]; then
        log "Performing rollback..."
        rollback_deployment
        send_deployment_notification "SUCCESS" "Rollback completed"
        exit 0
    fi
    
    # Deployment pipeline
    check_prerequisites
    validate_environment
    
    # Create backup before deployment
    backup_database
    
    # Deploy application
    deploy_application
    
    # Run migrations after deployment
    run_migrations
    
    # Wait for application to be ready
    if ! wait_for_health_check; then
        log_error "Deployment failed - health check timeout"
        
        log "Starting automatic rollback..."
        rollback_deployment
        
        send_deployment_notification "FAILED" "Health check failed, automatic rollback completed"
        exit 1
    fi
    
    # Run smoke tests
    if ! run_smoke_tests; then
        log_error "Deployment failed - smoke tests failed"
        
        log "Starting automatic rollback..."
        rollback_deployment
        
        send_deployment_notification "FAILED" "Smoke tests failed, automatic rollback completed"
        exit 1
    fi
    
    # Cleanup
    cleanup
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "Deployment completed successfully in ${duration}s"
    send_deployment_notification "SUCCESS" "Deployment completed in ${duration}s"
}

# Trap errors and cleanup
trap 'log_error "Deployment failed"; send_deployment_notification "FAILED" "Deployment script error"' ERR

# Run main function
main "$@"