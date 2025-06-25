# MBA Job Hunter 🎯

A streamlined job hunting platform for MBA graduates and professionals seeking product management, consulting, and strategy roles.

## Features

### 🔍 Job Discovery
- **Web Scraping**: Automated job collection from Indeed and other platforms
- **Smart Search**: Advanced filtering by salary, location, and experience level
- **Clean Data**: Processed and structured job information

### 🤖 AI Analysis
- **Job Matching**: AI-powered compatibility scoring
- **Market Insights**: Salary and trend analysis
- **Smart Recommendations**: Personalized application advice

### 📊 Integration
- **Notion Export**: Seamless integration with Notion databases
- **API Access**: RESTful API for job data and analysis
- **Clean Interface**: Simple and intuitive design

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (optional, SQLite by default)
- OpenAI API key
- Notion API key (optional)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/mba-job-hunter.git
cd mba-job-hunter
```

2. **Set up the backend**
```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

4. **Initialize database**
```bash
alembic upgrade head
```

5. **Run the application**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Core Endpoints
- **GET** `/health` - Health check
- **GET** `/api/v1/jobs/` - List jobs
- **GET** `/api/v1/jobs/search` - Search jobs
- **POST** `/api/v1/analysis/` - Analyze job matches

### Documentation
- **API Docs**: `http://localhost:8000/api/docs`
- **Health Check**: `http://localhost:8000/health`

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=sqlite:///./app.db

# OpenAI API
OPENAI_API_KEY=your_openai_key

# Notion (optional)
NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id

# Application
DEBUG=true
LOG_LEVEL=INFO
```

### Job Search Keywords
Edit `config/keywords.json` to customize job search terms:
```json
{
  "primary": ["Product Manager", "Strategy", "Consultant"],
  "secondary": ["MBA", "Business Strategy", "Product Strategy"]
}
```

## Project Structure

```
mba-job-hunter/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Configuration and setup
│   │   ├── models/          # Database models
│   │   ├── schemas/         # Data validation
│   │   ├── services/        # Business logic
│   │   ├── repositories/    # Data access layer
│   │   ├── scrapers/        # Web scraping
│   │   └── utils/           # Utilities
│   ├── tests/               # Test suite
│   ├── alembic/             # Database migrations
│   └── requirements.txt     # Dependencies
└── config/                  # Configuration files
```

## Development

### Running Tests
```bash
cd backend
pytest
```

### Code Quality
```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
flake8 app/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

The application will be available at `http://localhost:8000`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For questions or issues, please open an issue on GitHub or contact the development team.

---

**Note**: This is a simplified, production-ready version of the MBA Job Hunter platform, focused on core functionality and maintainability.