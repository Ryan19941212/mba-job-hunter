#!/bin/bash

# 🚀 MBA Job Hunter - Quick Deployment Setup Script
# This script helps you set up the deployment environment quickly

set -e

echo "🚀 MBA Job Hunter - Deployment Setup"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if running in correct directory
if [ ! -f "backend/requirements.txt" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_info "Setting up deployment environment..."

# Create necessary directories
mkdir -p logs
mkdir -p backups
mkdir -p k8s/production
mkdir -p k8s/staging

print_status "Created necessary directories"

# Check for required tools
echo ""
print_info "Checking required tools..."

command -v docker >/dev/null 2>&1 || {
    print_error "Docker is required but not installed. Please install Docker first."
    exit 1
}
print_status "Docker is installed"

command -v docker-compose >/dev/null 2>&1 || {
    print_warning "docker-compose not found. Checking for 'docker compose'..."
    docker compose version >/dev/null 2>&1 || {
        print_error "Docker Compose is required but not installed."
        exit 1
    }
}
print_status "Docker Compose is available"

# Check if git is configured
if [ -z "$(git config user.name)" ] || [ -z "$(git config user.email)" ]; then
    print_warning "Git user not configured. Please run:"
    echo "  git config --global user.name 'Your Name'"
    echo "  git config --global user.email 'your.email@example.com'"
fi

# Environment setup
echo ""
print_info "Setting up environment files..."

# Backend environment
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    print_status "Created backend/.env from example"
    print_warning "Please edit backend/.env with your actual configuration"
else
    print_info "backend/.env already exists"
fi

# Generate a secure secret key
if command -v openssl >/dev/null 2>&1; then
    SECRET_KEY=$(openssl rand -hex 32)
    print_status "Generated secure secret key"
else
    SECRET_KEY="dev-secret-key-please-change-in-production-$(date +%s)"
    print_warning "OpenSSL not found. Using basic secret key."
fi

# Update .env with generated secret key
if grep -q "your-super-secret-key" backend/.env; then
    sed -i.bak "s/your-super-secret-key-change-this-in-production-32-chars-min/$SECRET_KEY/" backend/.env
    print_status "Updated secret key in .env file"
fi

# Database setup instructions
echo ""
print_info "Database setup instructions:"
echo "1. Install PostgreSQL and Redis locally, or"
echo "2. Use Docker services: cd backend && docker-compose up -d postgres redis"
echo "3. Update DATABASE_URL and REDIS_URL in backend/.env"

# GitHub Secrets checklist
echo ""
print_info "GitHub Secrets Setup Checklist:"
echo "Go to GitHub repo → Settings → Secrets and variables → Actions"
echo ""
echo "Required secrets:"
echo "  🔑 OPENAI_API_KEY=sk-your_openai_api_key"
echo "  🔐 SECRET_KEY=$SECRET_KEY"
echo "  🗃️ DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db"
echo "  📊 REDIS_URL=redis://host:6379/0"
echo ""
echo "Optional secrets:"
echo "  📝 NOTION_API_KEY=secret_your_notion_token"
echo "  🚄 RAILWAY_TOKEN=your_railway_token"
echo "  📢 SLACK_WEBHOOK_URL=https://hooks.slack.com/..."
echo "  🐛 SENTRY_DSN=https://your-sentry-dsn..."

# API Keys setup instructions
echo ""
print_info "API Keys Setup Instructions:"
echo ""
echo "1. OpenAI API Key (Required):"
echo "   - Visit: https://platform.openai.com/api-keys"
echo "   - Create new secret key"
echo "   - Add to GitHub Secrets as OPENAI_API_KEY"
echo ""
echo "2. Notion API Key (Optional):"
echo "   - Visit: https://developers.notion.com/docs/create-a-notion-integration"
echo "   - Create new integration"
echo "   - Copy Internal Integration Token"
echo "   - Add to GitHub Secrets as NOTION_API_KEY"
echo ""
echo "3. Railway Token (for deployment):"
echo "   - Visit: https://railway.app/account/tokens"
echo "   - Generate new token"
echo "   - Add to GitHub Secrets as RAILWAY_TOKEN"

# Deployment platform options
echo ""
print_info "Deployment Platform Options:"
echo ""
echo "🚄 Railway (Recommended for beginners):"
echo "   - Easy setup with GitHub integration"
echo "   - Automatic SSL certificates"
echo "   - Built-in PostgreSQL and Redis"
echo "   - Visit: https://railway.app"
echo ""
echo "☸️  Kubernetes (Advanced):"
echo "   - Complete control over infrastructure"
echo "   - Requires kubeconfig setup"
echo "   - Blue-green deployment included"
echo ""
echo "🐳 Docker Hub + VPS:"
echo "   - Custom server deployment"
echo "   - Manual infrastructure management"
echo "   - Cost-effective for high traffic"

# Testing instructions
echo ""
print_info "Testing Your Setup:"
echo ""
echo "1. Local development:"
echo "   cd backend"
echo "   make dev  # or docker-compose up -d"
echo "   curl http://localhost:8000/api/v1/health"
echo ""
echo "2. Run tests:"
echo "   cd backend"
echo "   make test  # or pytest"
echo ""
echo "3. Check CI/CD pipeline:"
echo "   git push origin main"
echo "   # Check GitHub Actions tab"

# Security checklist
echo ""
print_info "Security Checklist:"
echo "  ✅ Never commit .env files"
echo "  ✅ Use strong secret keys (32+ characters)"
echo "  ✅ Enable 2FA on GitHub account"
echo "  ✅ Regularly rotate API keys"
echo "  ✅ Monitor security alerts"
echo "  ✅ Keep dependencies updated"

# Final steps
echo ""
print_info "Next Steps:"
echo "1. 📝 Edit backend/.env with your database URLs"
echo "2. 🔑 Add required secrets to GitHub repository"
echo "3. 🧪 Test local setup: make dev && make test"
echo "4. 🚀 Push to GitHub to trigger CI/CD pipeline"
echo "5. 📊 Monitor deployment in GitHub Actions"

echo ""
print_status "Setup script completed!"
print_info "For detailed instructions, see DEPLOYMENT.md"
print_info "For troubleshooting, check the logs in GitHub Actions"

# Save configuration summary
cat > deployment-summary.txt << EOF
MBA Job Hunter - Deployment Summary
Generated: $(date)

Secret Key: $SECRET_KEY
Project Structure: ✅ Created
Environment Files: ✅ Created
Docker Services: Ready
CI/CD Pipeline: Configured

Next Steps:
1. Configure GitHub Secrets
2. Update backend/.env
3. Test local setup
4. Deploy via GitHub Actions

EOF

print_status "Deployment summary saved to deployment-summary.txt"
echo ""
echo "🎉 Happy deploying!"