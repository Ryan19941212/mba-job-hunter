# MBA Job Hunter Backend - Makefile
# This Makefile provides convenient commands for Docker operations and development tasks

# Variables
DOCKER_COMPOSE = docker compose
DOCKER_COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.override.yml
DOCKER_COMPOSE_PROD = docker compose -f docker-compose.yml
PROJECT_NAME = mba-job-hunter
BUILD_DATE = $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
VERSION = $(shell git describe --tags --always --dirty)
VCS_REF = $(shell git rev-parse --short HEAD)

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

##@ Help
help: ## Display this help
	@echo "$(GREEN)MBA Job Hunter Backend - Docker Management$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development
dev: ## Start development environment with hot reload
	@echo "$(GREEN)Starting development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN)Development services started!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

dev-build: ## Build development environment
	@echo "$(GREEN)Building development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) build \
		--build-arg ENVIRONMENT=development \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg VERSION=$(VERSION) \
		--build-arg VCS_REF=$(VCS_REF)

dev-logs: ## Show development logs
	$(DOCKER_COMPOSE_DEV) logs -f

dev-shell: ## Access development container shell
	$(DOCKER_COMPOSE_DEV) exec api bash

dev-stop: ## Stop development environment
	@echo "$(YELLOW)Stopping development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) down

dev-restart: ## Restart development environment
	@echo "$(YELLOW)Restarting development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) restart

dev-clean: ## Clean development environment (remove containers and volumes)
	@echo "$(RED)Cleaning development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) down -v --remove-orphans
	docker system prune -f

##@ Production
build: ## Build production images
	@echo "$(GREEN)Building production images...$(NC)"
	$(DOCKER_COMPOSE_PROD) build \
		--build-arg ENVIRONMENT=production \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg VERSION=$(VERSION) \
		--build-arg VCS_REF=$(VCS_REF)

up: ## Start production environment
	@echo "$(GREEN)Starting production environment...$(NC)"
	$(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)Production services started!$(NC)"

down: ## Stop production environment
	@echo "$(YELLOW)Stopping production environment...$(NC)"
	$(DOCKER_COMPOSE_PROD) down

restart: ## Restart production environment
	@echo "$(YELLOW)Restarting production environment...$(NC)"
	$(DOCKER_COMPOSE_PROD) restart

logs: ## Show production logs
	$(DOCKER_COMPOSE_PROD) logs -f

shell: ## Access production container shell
	$(DOCKER_COMPOSE_PROD) exec api bash

##@ Database
db-shell: ## Access database shell
	$(DOCKER_COMPOSE_DEV) exec postgres psql -U postgres -d mba_job_hunter_dev

db-backup: ## Backup database
	@echo "$(GREEN)Creating database backup...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec postgres pg_dump -U postgres mba_job_hunter_dev > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore: ## Restore database from backup (usage: make db-restore FILE=backup.sql)
	@echo "$(GREEN)Restoring database from $(FILE)...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec -T postgres psql -U postgres mba_job_hunter_dev < $(FILE)

db-reset: ## Reset database (WARNING: This will delete all data)
	@echo "$(RED)Resetting database...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS mba_job_hunter_dev;"
	$(DOCKER_COMPOSE_DEV) exec postgres psql -U postgres -c "CREATE DATABASE mba_job_hunter_dev;"

##@ Tools
tools: ## Start development tools (pgAdmin, Redis Commander, etc.)
	@echo "$(GREEN)Starting development tools...$(NC)"
	$(DOCKER_COMPOSE_DEV) --profile tools up -d
	@echo "$(GREEN)Development tools started!$(NC)"
	@echo "pgAdmin: http://localhost:8080 (admin@admin.com / admin)"
	@echo "Redis Commander: http://localhost:8081"
	@echo "Jupyter Lab: http://localhost:8888 (token: dev-token)"
	@echo "MailHog: http://localhost:8025"

tools-stop: ## Stop development tools
	@echo "$(YELLOW)Stopping development tools...$(NC)"
	$(DOCKER_COMPOSE_DEV) --profile tools down

##@ Testing
test: ## Run tests in container
	@echo "$(GREEN)Running tests...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec api python -m pytest tests/ -v

test-coverage: ## Run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec api python -m pytest tests/ --cov=app --cov-report=html --cov-report=term

lint: ## Run linting
	@echo "$(GREEN)Running linting...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec api black app/ tests/
	$(DOCKER_COMPOSE_DEV) exec api flake8 app/ tests/
	$(DOCKER_COMPOSE_DEV) exec api mypy app/

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec api black app/ tests/
	$(DOCKER_COMPOSE_DEV) exec api isort app/ tests/

##@ Maintenance
status: ## Show container status
	$(DOCKER_COMPOSE_DEV) ps

health: ## Check service health
	@echo "$(GREEN)Checking service health...$(NC)"
	@curl -f http://localhost:8000/api/v1/health || echo "$(RED)API health check failed$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec postgres pg_isready -U postgres || echo "$(RED)Database health check failed$(NC)"
	@$(DOCKER_COMPOSE_DEV) exec redis redis-cli ping || echo "$(RED)Redis health check failed$(NC)"

clean: ## Clean Docker system
	@echo "$(RED)Cleaning Docker system...$(NC)"
	docker system prune -f
	docker volume prune -f
	docker network prune -f

clean-all: ## Clean everything (containers, volumes, images)
	@echo "$(RED)Cleaning everything...$(NC)"
	$(DOCKER_COMPOSE_DEV) down -v --remove-orphans
	docker system prune -af
	docker volume prune -f
	docker network prune -f

update: ## Update and rebuild containers
	@echo "$(GREEN)Updating containers...$(NC)"
	$(DOCKER_COMPOSE_DEV) pull
	$(DOCKER_COMPOSE_DEV) build --no-cache
	$(DOCKER_COMPOSE_DEV) up -d

##@ Production Deployment
deploy-prod: ## Deploy to production
	@echo "$(GREEN)Deploying to production...$(NC)"
	$(DOCKER_COMPOSE_PROD) pull
	$(DOCKER_COMPOSE_PROD) up -d --remove-orphans
	@echo "$(GREEN)Production deployment complete!$(NC)"

backup-prod: ## Backup production data
	@echo "$(GREEN)Creating production backup...$(NC)"
	$(DOCKER_COMPOSE_PROD) exec postgres pg_dump -U postgres mba_job_hunter > prod_backup_$(shell date +%Y%m%d_%H%M%S).sql
	$(DOCKER_COMPOSE_PROD) exec redis redis-cli --rdb /data/dump_$(shell date +%Y%m%d_%H%M%S).rdb

##@ Information
env: ## Show environment information
	@echo "$(GREEN)Environment Information:$(NC)"
	@echo "Project: $(PROJECT_NAME)"
	@echo "Build Date: $(BUILD_DATE)"
	@echo "Version: $(VERSION)"
	@echo "VCS Ref: $(VCS_REF)"
	@echo "Docker Compose Version: $(shell $(DOCKER_COMPOSE) version --short)"

ports: ## Show exposed ports
	@echo "$(GREEN)Exposed Ports:$(NC)"
	@echo "API (Development): http://localhost:8000"
	@echo "API (Production): http://localhost:8000"
	@echo "Database (Development): localhost:5433"
	@echo "Database (Production): localhost:5432"
	@echo "Redis (Development): localhost:6380"
	@echo "Redis (Production): localhost:6379"
	@echo "pgAdmin: http://localhost:8080"
	@echo "Redis Commander: http://localhost:8081"
	@echo "Jupyter Lab: http://localhost:8888"
	@echo "MailHog: http://localhost:8025"

##@ Shortcuts
start: dev ## Alias for dev
stop: dev-stop ## Alias for dev-stop
rebuild: dev-clean dev-build dev ## Clean, build and start development

.PHONY: help dev dev-build dev-logs dev-shell dev-stop dev-restart dev-clean \
        build up down restart logs shell \
        db-shell db-backup db-restore db-reset \
        tools tools-stop \
        test test-coverage lint format \
        status health clean clean-all update \
        deploy-prod backup-prod \
        env ports \
        start stop rebuild