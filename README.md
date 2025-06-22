# MBA Job Hunter 🎯

A comprehensive job hunting platform designed specifically for MBA graduates and professionals seeking product management, consulting, and strategy roles.

## Features

### 🔍 Smart Job Discovery
- **Multi-Platform Scraping**: Automated job collection from Indeed, LinkedIn, and Levels.fyi
- **Intelligent Filtering**: Advanced search with salary, location, experience level, and company filters
- **Real-time Updates**: Fresh job postings updated daily

### 🤖 AI-Powered Analysis
- **Job Matching**: AI-driven compatibility scoring based on your profile and preferences
- **Market Insights**: Trend analysis and salary benchmarking
- **Application Optimization**: Personalized recommendations for each opportunity

### 📊 Professional Tracking
- **Notion Integration**: Seamless export to Notion databases
- **Application Management**: Track applications, interviews, and follow-ups
- **Performance Analytics**: Success metrics and improvement suggestions

### 🎯 MBA-Focused
- **Target Roles**: Product Manager, Consultant, Strategy roles, Investment Banking, Private Equity
- **Top Companies**: FAANG, Big 4 Consulting, Investment Banks, Unicorn Startups
- **Premium Positions**: Senior and leadership opportunities

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Docker (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd mba-job-hunter
```

2. **Set up environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Install dependencies**
```bash
cd backend
pip install -r requirements.txt
```

4. **Set up database**
```bash
# Run database migrations
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_data.py
```

5. **Configure your profile**
```bash
cp config/user_profile.json.example config/user_profile.json
# Edit with your information and preferences
```

6. **Start the application**
```bash
# Development server
uvicorn app.main:app --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuration

### Environment Variables
Create a `.env` file based on `.env.example`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mba_job_hunter
REDIS_URL=redis://localhost:6379

# API Keys
OPENAI_API_KEY=your_openai_api_key
NOTION_API_KEY=your_notion_api_key
INDEED_API_KEY=your_indeed_api_key

# Security
SECRET_KEY=your_very_long_secret_key_here
```

### User Profile
Configure your preferences in `config/user_profile.json`:

```json
{
  "personal_info": {
    "name": "Your Name",
    "location": "San Francisco, CA"
  },
  "preferences": {
    "target_roles": ["Senior Product Manager", "Principal Product Manager"],
    "preferred_companies": ["Google", "Meta", "Amazon"],
    "salary_range": {"min": 150000, "max": 300000}
  }
}
```

## API Documentation

Once running, visit:
- **API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints

```http
GET /api/v1/jobs          # Search and filter jobs
GET /api/v1/jobs/{id}     # Get job details
POST /api/v1/analysis/job/{id}  # Analyze job match
GET /api/v1/analysis/matches    # Get personalized matches
```

## Development

### Project Structure
```
mba-job-hunter/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Configuration, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── scrapers/     # Job board scrapers
│   │   ├── services/     # Business logic
│   │   └── utils/        # Utilities
│   ├── tests/            # Test suite
│   └── alembic/          # Database migrations
├── config/               # Configuration files
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

### Running Tests
```bash
cd backend
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Code Quality
```bash
# Linting
flake8 app/

# Type checking
mypy app/

# Formatting
black app/
```

## Scraping Setup

### LinkedIn Scraping
```bash
# Set up LinkedIn credentials
export LINKEDIN_EMAIL=your_email@example.com
export LINKEDIN_PASSWORD=your_password

# Install browser drivers
playwright install chromium
```

### Rate Limiting
- Indeed: 1000 requests/day
- LinkedIn: 100 requests/hour
- Levels.fyi: 500 requests/day

## Deployment

### Docker
```bash
# Build and run
docker-compose up --build

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment
```bash
# Install production dependencies
pip install -r requirements.txt

# Set environment
export ENVIRONMENT=production

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Monitoring

### Health Checks
```http
GET /health          # Basic health check
GET /health/detailed # Detailed system status
GET /metrics         # Application metrics
```

### Logging
Logs are structured JSON format:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Job analysis completed",
  "job_id": 123,
  "user_id": "user_456"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add type hints to all functions
- Write comprehensive docstrings
- Include tests for new features
- Update documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@mbajobhunter.com
- 💬 Discord: [Join our community](https://discord.gg/mbajobhunter)
- 📖 Documentation: [Full docs](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/mbajobhunter/issues)

## Roadmap

### Q1 2024
- [ ] Chrome extension for one-click job saving
- [ ] Mobile app (React Native)
- [ ] Advanced salary negotiation insights

### Q2 2024
- [ ] Resume optimization suggestions
- [ ] Interview preparation AI
- [ ] Network referral matching

### Q3 2024
- [ ] Company culture analysis
- [ ] Equity package evaluation
- [ ] Career progression planning

---

**Built with ❤️ for MBA professionals seeking their next great opportunity**