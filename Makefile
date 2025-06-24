# MBA Job Hunter - Project Makefile
# This Makefile provides convenient commands for development and deployment

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
BLUE = \033[0;34m
NC = \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

##@ Help
help: ## Display this help
	@echo "$(GREEN)MBA Job Hunter - Project Management$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup
setup: ## Run initial project setup
	@echo "$(GREEN)🚀 Running project setup...$(NC)"
	@./scripts/setup-deployment.sh

install: ## Install project dependencies
	@echo "$(GREEN)📦 Installing dependencies...$(NC)"
	cd backend && pip install -r requirements-dev.txt

##@ Development
dev: ## Start development environment
	@echo "$(GREEN)🔄 Starting development environment...$(NC)"
	cd backend && make dev

test: ## Run tests
	@echo "$(GREEN)🧪 Running tests...$(NC)"
	cd backend && make test

lint: ## Run code linting
	@echo "$(GREEN)🔧 Running linters...$(NC)"
	cd backend && make lint

format: ## Format code
	@echo "$(GREEN)🎨 Formatting code...$(NC)"
	cd backend && make format

##@ Validation
validate: ## Validate environment configuration
	@echo "$(GREEN)🔍 Validating environment...$(NC)"
	cd backend && python ../scripts/validate-environment.py

check-secrets: ## Check if GitHub secrets are configured
	@echo "$(GREEN)🔑 Checking GitHub secrets...$(NC)"
	@echo "Run this command to trigger secrets validation:"
	@echo "gh workflow run secrets-check.yml"

##@ Docker
docker-build: ## Build Docker images
	@echo "$(GREEN)🐳 Building Docker images...$(NC)"
	cd backend && docker-compose build

docker-up: ## Start Docker services
	@echo "$(GREEN)🚀 Starting Docker services...$(NC)"
	cd backend && docker-compose up -d

docker-down: ## Stop Docker services
	@echo "$(GREEN)🛑 Stopping Docker services...$(NC)"
	cd backend && docker-compose down

docker-logs: ## Show Docker logs
	@echo "$(GREEN)📋 Showing Docker logs...$(NC)"
	cd backend && docker-compose logs -f

##@ Deployment
deploy-staging: ## Deploy to staging (trigger manually)
	@echo "$(GREEN)🧪 Triggering staging deployment...$(NC)"
	@echo "Pushing to main branch will trigger staging deployment"
	git push origin main

deploy-production: ## Deploy to production (requires manual approval)
	@echo "$(GREEN)🌟 Triggering production deployment...$(NC)"
	gh workflow run cd.yml -f environment=production

create-release: ## Create a new release
	@echo "$(GREEN)🏷️ Creating new release...$(NC)"
	@read -p "Enter version (e.g., v1.0.0): " version; \
	git tag -a $$version -m "Release $$version"; \
	git push origin $$version

##@ Database
db-migrate: ## Run database migrations
	@echo "$(GREEN)🗃️ Running database migrations...$(NC)"
	cd backend && alembic upgrade head

db-downgrade: ## Downgrade database by one revision
	@echo "$(YELLOW)⬇️ Downgrading database...$(NC)"
	cd backend && alembic downgrade -1

db-reset: ## Reset database (WARNING: destructive)
	@echo "$(RED)⚠️ This will reset the database!$(NC)"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		cd backend && make db-reset; \
	else \
		echo "Cancelled."; \
	fi

##@ Security
security-scan: ## Run security scans locally
	@echo "$(GREEN)🔒 Running security scans...$(NC)"
	cd backend && bandit -r app/
	cd backend && safety check
	
secret-generate: ## Generate secure secret key
	@echo "$(GREEN)🔑 Generating secure secret key...$(NC)"
	@python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

##@ Monitoring
logs: ## Show application logs
	@echo "$(GREEN)📋 Showing application logs...$(NC)"
	cd backend && tail -f logs/app.log

health: ## Check application health
	@echo "$(GREEN)🏥 Checking application health...$(NC)"
	@curl -f http://localhost:8000/api/v1/health || echo "$(RED)Health check failed$(NC)"

monitor: ## Monitor application status
	@echo "$(GREEN)📊 Monitoring application...$(NC)"
	@while true; do \
		curl -s http://localhost:8000/api/v1/health | jq '.status' || echo "$(RED)Service down$(NC)"; \
		sleep 30; \
	done

##@ Cleanup
clean: ## Clean up temporary files
	@echo "$(GREEN)🧹 Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	cd backend && docker system prune -f

clean-all: ## Clean everything including Docker volumes
	@echo "$(RED)🗑️ Cleaning everything...$(NC)"
	@make clean
	cd backend && docker-compose down -v
	docker system prune -af

##@ Information
status: ## Show project status
	@echo "$(GREEN)📊 Project Status$(NC)"
	@echo "==================="
	@echo "Git branch: $(shell git branch --show-current)"
	@echo "Git status: $(shell git status --porcelain | wc -l) changed files"
	@echo "Last commit: $(shell git log -1 --pretty=format:'%h - %s (%cr)')"
	@echo ""
	@echo "$(GREEN)Services Status:$(NC)"
	@echo "API: $(shell curl -s http://localhost:8000/api/v1/health | jq -r '.status' 2>/dev/null || echo 'Not running')"
	@echo "Database: $(shell cd backend && docker-compose ps postgres | grep -q 'Up' && echo 'Running' || echo 'Not running')"
	@echo "Redis: $(shell cd backend && docker-compose ps redis | grep -q 'Up' && echo 'Running' || echo 'Not running')"

env-info: ## Show environment information
	@echo "$(GREEN)🌍 Environment Information$(NC)"
	@echo "=========================="
	@echo "Python: $(shell python3 --version)"
	@echo "Docker: $(shell docker --version)"
	@echo "Docker Compose: $(shell docker-compose --version 2>/dev/null || docker compose version)"
	@echo "Git: $(shell git --version)"
	@echo "Node.js: $(shell node --version 2>/dev/null || echo 'Not installed')"
	@echo ""
	@echo "Environment variables:"
	@echo "ENVIRONMENT: $(shell echo $$ENVIRONMENT)"
	@echo "DEBUG: $(shell echo $$DEBUG)"

##@ Documentation
docs: ## Generate project documentation
	@echo "$(GREEN)📚 Generating documentation...$(NC)"
	@echo "See DEPLOYMENT.md for deployment instructions"
	@echo "See README.md for project overview"

##@ Shortcuts
start: docker-up ## Start all services
stop: docker-down ## Stop all services
restart: docker-down docker-up ## Restart all services
backend: ## Access backend directory
	@cd backend

.PHONY: help setup install dev test lint format validate check-secrets \
        docker-build docker-up docker-down docker-logs \
        deploy-staging deploy-production create-release \
        db-migrate db-downgrade db-reset \
        security-scan secret-generate \
        logs health monitor \
        clean clean-all \
        status env-info docs \
        start stop restart backend