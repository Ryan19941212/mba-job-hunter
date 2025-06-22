"""
Base Scraper Classes

Abstract base classes and utilities for job board scrapers.
Provides common functionality and interface for all scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import asyncio
import time
from dataclasses import dataclass
from enum import Enum

import httpx
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from app.core.config import get_settings
from app.utils.logger import get_logger

# Initialize logger and settings
logger = get_logger(__name__)
settings = get_settings()


class ScraperType(Enum):
    """Types of scrapers available."""
    HTTP_ONLY = "http_only"
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"


@dataclass
class JobData:
    """Standardized job data structure."""
    
    title: str
    company_name: str
    location: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    salary_period: Optional[str] = None
    
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    
    source: Optional[str] = None
    source_job_id: Optional[str] = None
    source_url: Optional[str] = None
    
    skills_required: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    
    is_remote: bool = False
    
    additional_info: Optional[Dict[str, Any]] = None


@dataclass
class ScrapingConfig:
    """Configuration for scraping operations."""
    
    max_pages: int = 10
    delay_between_requests: float = 2.0
    timeout_seconds: int = 30
    max_retries: int = 3
    
    use_proxy: bool = False
    proxy_list: Optional[List[str]] = None
    
    headless: bool = True
    user_agent: Optional[str] = None
    
    rate_limit_per_minute: int = 30
    respect_robots_txt: bool = True


class ScrapingError(Exception):
    """Base exception for scraping errors."""
    pass


class RateLimitError(ScrapingError):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(ScrapingError):
    """Raised when authentication fails."""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for job board scrapers.
    
    Provides common functionality and interface that all scrapers must implement.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None) -> None:
        """
        Initialize the scraper.
        
        Args:
            config: Scraping configuration
        """
        self.config = config or ScrapingConfig()
        self.session: Optional[httpx.AsyncClient] = None
        self.driver: Optional[webdriver.Chrome] = None
        
        # Rate limiting
        self._request_times: List[float] = []
        self._last_request_time = 0.0
        
        # Statistics
        self._stats = {
            "jobs_found": 0,
            "jobs_processed": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Scraper name."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the job board."""
        pass
    
    @property
    @abstractmethod
    def scraper_type(self) -> ScraperType:
        """Type of scraper (HTTP, Selenium, etc.)."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def initialize(self) -> None:
        """Initialize scraper resources."""
        self._stats["start_time"] = datetime.utcnow()
        
        if self.scraper_type == ScraperType.HTTP_ONLY:
            await self._initialize_http_client()
        elif self.scraper_type == ScraperType.SELENIUM:
            await self._initialize_selenium()
        
        logger.info(f"Initialized {self.name} scraper")
    
    async def cleanup(self) -> None:
        """Cleanup scraper resources."""
        self._stats["end_time"] = datetime.utcnow()
        
        if self.session:
            await self.session.aclose()
        
        if self.driver:
            self.driver.quit()
        
        duration = (self._stats["end_time"] - self._stats["start_time"]).total_seconds()
        logger.info(
            f"Scraper {self.name} completed in {duration:.2f}s. "
            f"Found: {self._stats['jobs_found']}, "
            f"Processed: {self._stats['jobs_processed']}, "
            f"Errors: {self._stats['errors']}"
        )
    
    async def _initialize_http_client(self) -> None:
        """Initialize HTTP client."""
        headers = {
            "User-Agent": self.config.user_agent or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        
        self.session = httpx.AsyncClient(
            headers=headers,
            timeout=self.config.timeout_seconds,
            follow_redirects=True
        )
    
    async def _initialize_selenium(self) -> None:
        """Initialize Selenium WebDriver."""
        options = Options()
        
        if self.config.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        if self.config.user_agent:
            options.add_argument(f"--user-agent={self.config.user_agent}")
        
        # Run in separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        self.driver = await loop.run_in_executor(
            None, lambda: webdriver.Chrome(options=options)
        )
        
        self.driver.implicitly_wait(10)
    
    async def _rate_limit_check(self) -> None:
        """Check and enforce rate limiting."""
        current_time = time.time()
        
        # Remove requests older than 1 minute
        cutoff_time = current_time - 60
        self._request_times = [t for t in self._request_times if t > cutoff_time]
        
        # Check if we're at the limit
        if len(self._request_times) >= self.config.rate_limit_per_minute:
            sleep_time = 60 - (current_time - self._request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
        
        # Add delay between requests
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.config.delay_between_requests:
            delay = self.config.delay_between_requests - time_since_last
            await asyncio.sleep(delay)
        
        # Record this request
        self._request_times.append(current_time)
        self._last_request_time = current_time
    
    async def _make_http_request(
        self, 
        url: str, 
        method: str = "GET",
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with rate limiting and retry logic.
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional arguments for httpx
            
        Returns:
            httpx.Response: HTTP response
            
        Raises:
            ScrapingError: If request fails after retries
        """
        await self._rate_limit_check()
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError(f"Rate limited by {self.name}")
                elif e.response.status_code in [401, 403]:
                    raise AuthenticationError(f"Authentication failed for {self.name}")
                
                if attempt == self.config.max_retries - 1:
                    raise ScrapingError(f"HTTP error {e.response.status_code}: {e}")
                
                # Exponential backoff
                wait_time = (2 ** attempt) * self.config.delay_between_requests
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise ScrapingError(f"Request failed: {e}")
                
                wait_time = (2 ** attempt) * self.config.delay_between_requests
                await asyncio.sleep(wait_time)
    
    @abstractmethod
    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[JobData, None]:
        """
        Search for jobs on the job board.
        
        Args:
            query: Search query
            location: Location filter
            **kwargs: Additional search parameters
            
        Yields:
            JobData: Individual job postings
        """
        pass
    
    @abstractmethod
    async def get_job_details(self, job_url: str) -> Optional[JobData]:
        """
        Get detailed information for a specific job.
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Optional[JobData]: Detailed job information or None if failed
        """
        pass
    
    def _parse_salary(self, salary_text: str) -> Dict[str, Any]:
        """
        Parse salary information from text.
        
        Args:
            salary_text: Raw salary text
            
        Returns:
            Dict[str, Any]: Parsed salary information
        """
        import re
        
        result = {
            "min": None,
            "max": None,
            "currency": "USD",
            "period": None
        }
        
        if not salary_text:
            return result
        
        # Remove common prefixes/suffixes
        salary_text = re.sub(r'(salary|pay|compensation|per|hour|year|annual)', '', salary_text, flags=re.IGNORECASE)
        
        # Extract currency
        currency_match = re.search(r'([A-Z]{3}|\$|€|£)', salary_text)
        if currency_match:
            currency = currency_match.group(1)
            if currency == '$':
                result["currency"] = "USD"
            elif currency == '€':
                result["currency"] = "EUR"
            elif currency == '£':
                result["currency"] = "GBP"
            else:
                result["currency"] = currency
        
        # Extract period
        if re.search(r'(hour|hr|hourly)', salary_text, re.IGNORECASE):
            result["period"] = "hourly"
        elif re.search(r'(year|annual|yearly)', salary_text, re.IGNORECASE):
            result["period"] = "annual"
        elif re.search(r'(month|monthly)', salary_text, re.IGNORECASE):
            result["period"] = "monthly"
        
        # Extract numbers
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', salary_text.replace(',', ''))
        numbers = [float(n) for n in numbers if n]
        
        if len(numbers) == 1:
            # Single number - could be min or max
            if 'up to' in salary_text.lower():
                result["max"] = numbers[0]
            else:
                result["min"] = numbers[0]
        elif len(numbers) >= 2:
            # Range
            result["min"] = min(numbers)
            result["max"] = max(numbers)
        
        return result
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse posting date from text.
        
        Args:
            date_text: Raw date text
            
        Returns:
            Optional[datetime]: Parsed date or None
        """
        import re
        from dateutil import parser
        
        if not date_text:
            return None
        
        try:
            # Handle relative dates
            if 'ago' in date_text.lower():
                now = datetime.utcnow()
                
                # Extract number and unit
                match = re.search(r'(\d+)\s*(day|hour|week|month)s?\s*ago', date_text.lower())
                if match:
                    number, unit = match.groups()
                    number = int(number)
                    
                    if unit == 'hour':
                        return now - timedelta(hours=number)
                    elif unit == 'day':
                        return now - timedelta(days=number)
                    elif unit == 'week':
                        return now - timedelta(weeks=number)
                    elif unit == 'month':
                        return now - timedelta(days=number * 30)
            
            # Try to parse absolute date
            return parser.parse(date_text, fuzzy=True)
            
        except Exception:
            return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """
        Extract skills from job description text.
        
        Args:
            text: Job description or requirements text
            
        Returns:
            List[str]: Extracted skills
        """
        if not text:
            return []
        
        # Common MBA/business skills
        skills_patterns = [
            r'\b(MBA|Master of Business Administration)\b',
            r'\b(SQL|Python|R|Excel|PowerBI|Tableau|Looker)\b',
            r'\b(Product Management|Product Manager|PM)\b',
            r'\b(Strategy|Strategic Planning|Business Strategy)\b',
            r'\b(Analytics|Data Analysis|Business Intelligence)\b',
            r'\b(Consulting|Management Consulting)\b',
            r'\b(Financial Modeling|Finance|Accounting)\b',
            r'\b(Marketing|Digital Marketing|Growth Marketing)\b',
            r'\b(Operations|Operations Management)\b',
            r'\b(Project Management|Agile|Scrum)\b',
            r'\b(Leadership|Team Management)\b',
            r'\b(Communication|Presentation)\b',
        ]
        
        skills = []
        text_lower = text.lower()
        
        for pattern in skills_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.group(0)
                if skill not in skills:
                    skills.append(skill)
        
        return skills[:20]  # Limit to top 20 skills
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return self._stats.copy()


class ScraperManager:
    """
    Manages multiple scrapers and coordinates scraping operations.
    """
    
    def __init__(self) -> None:
        """Initialize scraper manager."""
        self.scrapers: Dict[str, BaseScraper] = {}
        self._stats = {
            "total_jobs_found": 0,
            "total_jobs_processed": 0,
            "total_errors": 0,
            "scraper_stats": {}
        }
    
    def register_scraper(self, scraper: BaseScraper) -> None:
        """
        Register a scraper.
        
        Args:
            scraper: Scraper instance to register
        """
        self.scrapers[scraper.name] = scraper
        logger.info(f"Registered scraper: {scraper.name}")
    
    async def scrape_all(
        self,
        query: str,
        location: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[JobData, None]:
        """
        Scrape jobs from all registered scrapers.
        
        Args:
            query: Search query
            location: Location filter
            **kwargs: Additional search parameters
            
        Yields:
            JobData: Job postings from all scrapers
        """
        tasks = []
        
        for name, scraper in self.scrapers.items():
            task = asyncio.create_task(
                self._scrape_single(scraper, query, location, **kwargs)
            )
            tasks.append((name, task))
        
        # Collect results from all scrapers
        for name, task in tasks:
            try:
                async for job in await task:
                    self._stats["total_jobs_found"] += 1
                    yield job
                
                # Update stats
                scraper_stats = self.scrapers[name].get_stats()
                self._stats["scraper_stats"][name] = scraper_stats
                
            except Exception as e:
                logger.error(f"Error in scraper {name}: {e}")
                self._stats["total_errors"] += 1
    
    async def _scrape_single(
        self,
        scraper: BaseScraper,
        query: str,
        location: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[JobData, None]:
        """Scrape jobs from a single scraper."""
        async with scraper:
            async for job in scraper.search_jobs(query, location, **kwargs):
                yield job
    
    async def run_periodic_scraping(self) -> None:
        """Run periodic scraping based on configuration."""
        from app.core.config import load_keywords_config
        
        keywords_config = load_keywords_config()
        
        while True:
            try:
                for job_title in keywords_config.get("job_titles", []):
                    for location in keywords_config.get("locations", []):
                        async for job in self.scrape_all(job_title, location):
                            # Process job (save to database, etc.)
                            self._stats["total_jobs_processed"] += 1
                            logger.info(f"Processed job: {job.title} at {job.company_name}")
                
                # Sleep until next scraping cycle
                await asyncio.sleep(settings.SCRAPE_INTERVAL_HOURS * 3600)
                
            except Exception as e:
                logger.error(f"Error in periodic scraping: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall scraping statistics."""
        return self._stats.copy()