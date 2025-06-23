"""
Pytest configuration and shared fixtures for MBA Job Hunter tests.

Provides reusable test fixtures for database sessions, API clients,
mock services, and test data for comprehensive testing.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

# Import app modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.main import app
from app.core.database import Base, get_db
from app.core.config import get_settings
from app.models.job import Job
from app.models.company import Company
from app.services.notion_writer import NotionWriter
from app.scrapers.indeed import IndeedScraper
from app.scrapers.base import JobData, ScrapingConfig

# Test settings
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Configure pytest-asyncio
pytest_asyncio.asyncio_mode = "auto"


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a session-scoped event loop for async tests.
    
    This ensures all async tests share the same event loop,
    which is important for database connections and fixtures.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine with SQLite in-memory database.
    
    Uses SQLite for fast, isolated testing without requiring
    a separate test database server.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="session")
async def test_session_factory(test_engine):
    """Create async session factory for tests."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


@pytest.fixture
async def test_db(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide test database session with automatic rollback.
    
    Each test gets a fresh database session that is rolled back
    after the test completes, ensuring test isolation.
    """
    async with test_session_factory() as session:
        # Start a transaction
        transaction = await session.begin()
        
        yield session
        
        # Rollback the transaction
        await transaction.rollback()


@pytest.fixture
async def test_client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide test HTTP client with database dependency override.
    
    This client can be used to test API endpoints with a test database.
    """
    # Override the database dependency
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_notion_client():
    """
    Mock Notion API client for testing without real API calls.
    
    Provides realistic responses for common Notion operations.
    """
    mock_client = AsyncMock()
    
    # Mock database operations
    mock_client.databases.create.return_value = {
        "id": "test_database_id",
        "title": [{"text": {"content": "Test Database"}}],
        "properties": {}
    }
    
    mock_client.databases.retrieve.return_value = {
        "id": "test_database_id",
        "properties": {}
    }
    
    mock_client.databases.update.return_value = {
        "id": "test_database_id",
        "properties": {}
    }
    
    mock_client.databases.query.return_value = {
        "results": [],
        "has_more": False,
        "next_cursor": None
    }
    
    # Mock page operations
    mock_client.pages.create.return_value = {
        "id": "test_page_id",
        "properties": {},
        "created_time": datetime.now(timezone.utc).isoformat()
    }
    
    mock_client.pages.update.return_value = {
        "id": "test_page_id",
        "properties": {},
        "last_edited_time": datetime.now(timezone.utc).isoformat()
    }
    
    mock_client.pages.retrieve.return_value = {
        "id": "test_page_id",
        "properties": {}
    }
    
    # Mock blocks operations
    mock_client.blocks.children.list.return_value = {
        "results": [],
        "has_more": False,
        "next_cursor": None
    }
    
    mock_client.blocks.children.append.return_value = {
        "results": []
    }
    
    # Mock user operations
    mock_client.users.me.return_value = {
        "id": "test_user_id",
        "name": "Test User",
        "type": "person"
    }
    
    # Mock search
    mock_client.search.return_value = {
        "results": [],
        "has_more": False,
        "next_cursor": None
    }
    
    return mock_client


@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI API client for testing AI services.
    
    Provides realistic responses for chat completions and embeddings.
    """
    mock_client = AsyncMock()
    
    # Mock chat completions
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="This is a sample AI analysis of the job posting. "
                           "The role appears well-suited for MBA graduates with "
                           "strong analytical and strategic thinking skills."
                ),
                finish_reason="stop"
            )
        ],
        usage=MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
    )
    
    # Mock embeddings
    mock_client.embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(
                embedding=[0.1] * 1536,  # Standard OpenAI embedding size
                index=0
            )
        ],
        usage=MagicMock(
            prompt_tokens=10,
            total_tokens=10
        )
    )
    
    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic Claude API client for testing."""
    mock_client = AsyncMock()
    
    mock_client.messages.create.return_value = MagicMock(
        content=[
            MagicMock(
                text="This is a sample Claude analysis of the job posting. "
                     "The position requires strong business acumen and would "
                     "be excellent for recent MBA graduates."
            )
        ],
        usage=MagicMock(
            input_tokens=100,
            output_tokens=50
        )
    )
    
    return mock_client


@pytest.fixture
def mock_scraper():
    """
    Mock web scraper for testing without actual web requests.
    
    Provides realistic job data responses.
    """
    mock_scraper = AsyncMock(spec=IndeedScraper)
    
    # Mock scraper properties
    mock_scraper.name = "indeed"
    mock_scraper.base_url = "https://www.indeed.com"
    mock_scraper.scraper_type = "HTTP_ONLY"
    
    # Mock search jobs method
    async def mock_search_jobs(*args, **kwargs):
        """Return sample job data."""
        for i in range(3):  # Return 3 sample jobs
            yield JobData(
                title=f"Test Job {i+1}",
                company_name=f"Test Company {i+1}",
                location="Test City, ST",
                description=f"Test job description {i+1}",
                salary_min=80000 + (i * 10000),
                salary_max=120000 + (i * 10000),
                source="indeed",
                source_url=f"https://indeed.com/job{i+1}",
                skills_required=["Python", "SQL", "MBA"]
            )
    
    mock_scraper.search_jobs.side_effect = mock_search_jobs
    
    # Mock get job details
    mock_scraper.get_job_details.return_value = JobData(
        title="Detailed Test Job",
        company_name="Detailed Test Company",
        location="Detailed City, ST",
        description="Detailed job description with requirements",
        requirements="MBA required, 3+ years experience",
        salary_min=100000,
        salary_max=150000,
        source="indeed",
        source_url="https://indeed.com/detailed_job"
    )
    
    return mock_scraper


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for testing HTTP requests."""
    mock_client = AsyncMock()
    
    # Mock successful responses
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.content = b"<html><body>Test content</body></html>"
    mock_response.text = "<html><body>Test content</body></html>"
    mock_response.json.return_value = {"status": "success", "data": []}
    
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    mock_client.request.return_value = mock_response
    
    return mock_client


# Test Data Fixtures

@pytest.fixture
def sample_job_data() -> Dict[str, Any]:
    """
    Provide sample job data for testing.
    
    Returns comprehensive job data that can be used across different tests.
    """
    return {
        "title": "Senior Product Manager - MBA Required",
        "company_name": "TechCorp Inc",
        "location": "San Francisco, CA",
        "description": (
            "We are seeking a Senior Product Manager with strong analytical skills "
            "and strategic thinking. The ideal candidate will have an MBA and "
            "3+ years of product management experience."
        ),
        "requirements": (
            "• MBA from top-tier business school\n"
            "• 3+ years of product management experience\n"
            "• Strong analytical and strategic thinking skills\n"
            "• Experience with data-driven decision making"
        ),
        "responsibilities": (
            "• Define product strategy and roadmap\n"
            "• Work with engineering teams to deliver features\n"
            "• Analyze market trends and user feedback\n"
            "• Present to executive leadership"
        ),
        "salary_min": 140000,
        "salary_max": 180000,
        "salary_currency": "USD",
        "salary_period": "annual",
        "job_type": "Full-time",
        "experience_level": "Senior Level",
        "posted_date": datetime.now(timezone.utc),
        "application_deadline": None,
        "source": "indeed",
        "source_platform": "indeed",
        "source_job_id": "test_job_123",
        "source_url": "https://indeed.com/viewjob?jk=test_job_123",
        "company_logo_url": "https://example.com/logo.png",
        "skills_required": ["MBA", "Product Management", "Strategy", "Analytics", "Leadership"],
        "benefits": ["Health Insurance", "401k", "Flexible PTO", "Stock Options"],
        "is_remote": False,
        "ai_fit_score": 85,
        "ai_summary": "Excellent match for MBA graduates with product management aspirations.",
        "additional_info": {
            "company_size": "1000+",
            "industry": "Technology",
            "funding_stage": "Public"
        }
    }


@pytest.fixture
def sample_company_data() -> Dict[str, Any]:
    """Provide sample company data for testing."""
    return {
        "name": "TechCorp Inc",
        "industry": "Technology",
        "size": "1000-5000",
        "location": "San Francisco, CA",
        "website": "https://techcorp.com",
        "description": (
            "TechCorp is a leading technology company specializing in "
            "innovative software solutions for enterprise clients."
        ),
        "logo_url": "https://techcorp.com/logo.png",
        "linkedin_url": "https://linkedin.com/company/techcorp",
        "glassdoor_rating": 4.2,
        "founded_year": 2010,
        "funding_total": 50000000,
        "employee_count": 2500,
        "culture_tags": ["Innovation", "Collaboration", "Growth", "Work-Life Balance"]
    }


@pytest.fixture
def sample_notion_response() -> Dict[str, Any]:
    """Provide sample Notion API response for testing."""
    return {
        "object": "database",
        "id": "test_database_id",
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "title": [
            {
                "type": "text",
                "text": {
                    "content": "MBA Job Hunter - Test Database"
                }
            }
        ],
        "properties": {
            "Job Title": {
                "id": "title",
                "type": "title",
                "title": {}
            },
            "Company": {
                "id": "company",
                "type": "rich_text",
                "rich_text": {}
            },
            "Salary Min": {
                "id": "salary_min",
                "type": "number",
                "number": {
                    "format": "dollar"
                }
            }
        }
    }


@pytest.fixture
def sample_scraper_config() -> ScrapingConfig:
    """Provide sample scraper configuration for testing."""
    return ScrapingConfig(
        max_pages=2,
        delay_between_requests=0.1,  # Faster for tests
        timeout_seconds=10,
        max_retries=1,
        rate_limit_per_minute=100,  # Higher for tests
        headless=True,
        respect_robots_txt=False  # Skip for tests
    )


@pytest.fixture
def sample_job_list(sample_job_data) -> List[Dict[str, Any]]:
    """Provide a list of sample jobs for batch testing."""
    jobs = []
    for i in range(5):
        job = sample_job_data.copy()
        job["title"] = f"Test Job {i+1}"
        job["company_name"] = f"Test Company {i+1}"
        job["source_job_id"] = f"test_job_{i+1}"
        job["source_url"] = f"https://indeed.com/viewjob?jk=test_job_{i+1}"
        job["salary_min"] = 80000 + (i * 10000)
        job["salary_max"] = 120000 + (i * 10000)
        jobs.append(job)
    return jobs


# Database fixtures for specific models

@pytest.fixture
async def sample_job_in_db(test_db: AsyncSession, sample_job_data) -> Job:
    """Create a sample job in the test database."""
    job = Job(
        title=sample_job_data["title"],
        company_name=sample_job_data["company_name"],
        location=sample_job_data["location"],
        description=sample_job_data["description"],
        requirements=sample_job_data["requirements"],
        salary_min=sample_job_data["salary_min"],
        salary_max=sample_job_data["salary_max"],
        currency=sample_job_data["salary_currency"],
        job_level=sample_job_data["experience_level"],
        employment_type=sample_job_data["job_type"],
        remote_friendly=sample_job_data["is_remote"],
        posted_date=sample_job_data["posted_date"],
        source_url=sample_job_data["source_url"],
        source_platform=sample_job_data["source_platform"],
        company_logo_url=sample_job_data["company_logo_url"],
        ai_fit_score=sample_job_data["ai_fit_score"],
        ai_summary=sample_job_data["ai_summary"],
        extracted_skills=sample_job_data["skills_required"]
    )
    
    test_db.add(job)
    await test_db.commit()
    await test_db.refresh(job)
    
    return job


@pytest.fixture
async def sample_company_in_db(test_db: AsyncSession, sample_company_data) -> Company:
    """Create a sample company in the test database."""
    company = Company(
        name=sample_company_data["name"],
        industry=sample_company_data["industry"],
        size=sample_company_data["size"],
        location=sample_company_data["location"],
        website=sample_company_data["website"],
        description=sample_company_data["description"],
        logo_url=sample_company_data["logo_url"],
        linkedin_url=sample_company_data["linkedin_url"],
        glassdoor_rating=sample_company_data["glassdoor_rating"],
        founded_year=sample_company_data["founded_year"]
    )
    
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    
    return company


# Utility fixtures

@pytest.fixture
def temp_file():
    """Provide a temporary file for testing file operations."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(autouse=True)
def mock_settings():
    """
    Mock application settings for testing.
    
    This fixture automatically applies to all tests and provides
    safe test values for all configuration settings.
    """
    with patch('app.core.config.get_settings') as mock_get_settings:
        mock_settings = MagicMock()
        
        # Database settings
        mock_settings.DATABASE_URL = TEST_DATABASE_URL
        
        # API keys (use test values)
        mock_settings.NOTION_API_KEY = "test_notion_key"
        mock_settings.OPENAI_API_KEY = "test_openai_key"
        mock_settings.ANTHROPIC_API_KEY = "test_anthropic_key"
        
        # Notion settings
        mock_settings.NOTION_DATABASE_ID = "test_database_id"
        
        # Security settings
        mock_settings.SECRET_KEY = "test_secret_key"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        
        # App settings
        mock_settings.APP_NAME = "MBA Job Hunter Test"
        mock_settings.DEBUG = True
        mock_settings.TESTING = True
        
        # Scraping settings
        mock_settings.ENABLE_BACKGROUND_SCRAPING = False
        mock_settings.SCRAPE_INTERVAL_HOURS = 1
        mock_settings.MAX_PAGES_PER_SCRAPER = 2
        mock_settings.REQUEST_DELAY_SECONDS = 0.1
        
        mock_get_settings.return_value = mock_settings
        yield mock_settings


# Performance testing fixtures

@pytest.fixture
def performance_timer():
    """Utility for measuring test performance."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Markers for different test types

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "api: mark test as testing API endpoints"
    )
    config.addinivalue_line(
        "markers", "scraper: mark test as testing web scrapers"
    )
    config.addinivalue_line(
        "markers", "notion: mark test as testing Notion integration"
    )
    config.addinivalue_line(
        "markers", "ai: mark test as testing AI services"
    )