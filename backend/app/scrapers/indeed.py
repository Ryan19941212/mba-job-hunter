"""
Indeed Job Scraper

Specialized scraper for Indeed job board with anti-detection measures
and comprehensive job data extraction.
"""

import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from urllib.parse import urlencode, urlparse, parse_qs
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.scrapers.base import BaseScraper, JobData, ScrapingConfig, ScraperType, ScrapingError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IndeedScraper(BaseScraper):
    """
    Indeed job scraper with comprehensive job data extraction.
    
    Features:
    - Multiple search filters (location, salary, job type, etc.)
    - Anti-detection measures (user agents, delays, proxies)
    - Detailed job information extraction
    - Salary parsing and normalization
    - Skills extraction for MBA-focused roles
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None) -> None:
        """Initialize Indeed scraper."""
        super().__init__(config)
        
        # Indeed-specific configuration
        self._base_search_url = "https://www.indeed.com/jobs"
        self._job_detail_base = "https://www.indeed.com/viewjob"
        
        # User agents for rotation
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
        ]
        
        # Common MBA job keywords for relevance filtering
        self._mba_keywords = [
            'mba', 'business analyst', 'product manager', 'consultant', 'strategy',
            'business development', 'operations manager', 'project manager',
            'finance manager', 'marketing manager', 'business intelligence'
        ]
    
    @property
    def name(self) -> str:
        """Scraper name."""
        return "indeed"
    
    @property
    def base_url(self) -> str:
        """Base URL for Indeed."""
        return "https://www.indeed.com"
    
    @property
    def scraper_type(self) -> ScraperType:
        """Scraper type - uses HTTP requests with fallback to Selenium."""
        return ScraperType.HTTP_ONLY
    
    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[JobData, None]:
        """
        Search for jobs on Indeed.
        
        Args:
            query: Job search query
            location: Location filter
            **kwargs: Additional filters (salary_min, job_type, etc.)
            
        Yields:
            JobData: Individual job postings
        """
        logger.info(f"Starting Indeed job search for: {query} in {location}")
        
        try:
            search_params = self._build_search_params(query, location, **kwargs)
            page = 0
            max_pages = kwargs.get('max_pages', self.config.max_pages)
            
            while page < max_pages:
                search_params['start'] = page * 10  # Indeed uses 10 jobs per page
                
                search_url = f"{self._base_search_url}?{urlencode(search_params)}"
                logger.debug(f"Searching page {page + 1}: {search_url}")
                
                try:
                    response = await self._make_http_request(search_url)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    jobs = await self._extract_jobs_from_page(soup, search_url)
                    
                    if not jobs:
                        logger.info(f"No more jobs found on page {page + 1}")
                        break
                    
                    for job in jobs:
                        self._stats["jobs_found"] += 1
                        yield job
                    
                    logger.info(f"Processed page {page + 1}, found {len(jobs)} jobs")
                    page += 1
                    
                    # Check if there's a next page
                    if not self._has_next_page(soup):
                        logger.info("No more pages available")
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing page {page + 1}: {e}")
                    self._stats["errors"] += 1
                    break
                    
        except Exception as e:
            logger.error(f"Error in Indeed job search: {e}")
            raise ScrapingError(f"Indeed job search failed: {e}")
    
    async def get_job_details(self, job_url: str) -> Optional[JobData]:
        """
        Get detailed information for a specific job.
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Optional[JobData]: Detailed job information or None if failed
        """
        try:
            response = await self._make_http_request(job_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return await self._extract_detailed_job_info(soup, job_url)
            
        except Exception as e:
            logger.error(f"Error getting job details from {job_url}: {e}")
            return None
    
    def _build_search_params(
        self,
        query: str,
        location: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build search parameters for Indeed API."""
        params = {
            'q': query,
            'sort': kwargs.get('sort', 'date'),  # Sort by date by default
            'limit': 50,  # Maximum results per page
        }
        
        if location:
            params['l'] = location
        
        # Salary filter
        if kwargs.get('salary_min'):
            params['salary'] = f"{kwargs['salary_min']}+"
        
        # Job type filter
        if kwargs.get('job_type'):
            job_type_map = {
                'full_time': 'fulltime',
                'part_time': 'parttime',
                'contract': 'contract',
                'temporary': 'temporary',
                'internship': 'internship'
            }
            params['jt'] = job_type_map.get(kwargs['job_type'], kwargs['job_type'])
        
        # Experience level
        if kwargs.get('experience_level'):
            exp_map = {
                'entry_level': 'entry_level',
                'mid_level': 'mid_level',
                'senior_level': 'senior_level'
            }
            params['explvl'] = exp_map.get(kwargs['experience_level'])
        
        # Remote jobs filter
        if kwargs.get('remote_only'):
            params['remotejob'] = '1'
        
        # Date posted filter
        date_posted = kwargs.get('date_posted', '7')  # Default to last 7 days
        if date_posted:
            params['fromage'] = date_posted
        
        return params
    
    async def _extract_jobs_from_page(
        self,
        soup: BeautifulSoup,
        search_url: str
    ) -> List[JobData]:
        """Extract job listings from search results page."""
        jobs = []
        
        # Find job cards - Indeed uses different selectors
        job_cards = soup.find_all('div', {'data-jk': True}) or soup.find_all('a', {'data-jk': True})
        
        if not job_cards:
            # Try alternative selectors
            job_cards = soup.find_all('td', class_='resultContent')
        
        logger.debug(f"Found {len(job_cards)} job cards on page")
        
        for card in job_cards:
            try:
                job_data = await self._extract_job_from_card(card)
                if job_data and self._is_relevant_job(job_data):
                    jobs.append(job_data)
                    
            except Exception as e:
                logger.debug(f"Error extracting job from card: {e}")
                continue
        
        return jobs
    
    async def _extract_job_from_card(self, card) -> Optional[JobData]:
        """Extract job information from a job card element."""
        try:
            # Extract job ID
            job_id = card.get('data-jk') or card.find('a', {'data-jk': True})
            if hasattr(job_id, 'get'):
                job_id = job_id.get('data-jk')
            
            # Extract title
            title_elem = (
                card.find('h2', class_='jobTitle') or 
                card.find('a', {'data-jk': True}) or
                card.find('span', attrs={'title': True})
            )
            
            if not title_elem:
                return None
                
            title = title_elem.get_text(strip=True) if hasattr(title_elem, 'get_text') else str(title_elem.get('title', ''))
            
            # Extract company name
            company_elem = (
                card.find('span', class_='companyName') or
                card.find('a', {'data-testid': 'company-name'}) or
                card.find('div', class_='companyName')
            )
            
            company_name = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = (
                card.find('div', {'data-testid': 'job-location'}) or
                card.find('span', class_='locationsContainer') or
                card.find('div', class_='companyLocation')
            )
            
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Extract salary if available
            salary_elem = card.find('span', class_='salaryText') or card.find('div', class_='salary-snippet')
            salary_info = self._parse_salary(salary_elem.get_text(strip=True)) if salary_elem else {}
            
            # Extract job snippet/description
            snippet_elem = (
                card.find('div', class_='job-snippet') or
                card.find('span', class_='summary') or
                card.find('div', {'data-testid': 'job-snippet'})
            )
            
            description = snippet_elem.get_text(strip=True) if snippet_elem else None
            
            # Extract posting date
            date_elem = card.find('span', class_='date')
            posted_date = self._parse_date(date_elem.get_text(strip=True)) if date_elem else None
            
            # Build job URL
            job_url = f"{self._job_detail_base}?jk={job_id}" if job_id else None
            
            # Determine if remote
            is_remote = self._is_remote_job(location, description)
            
            # Extract skills from description
            skills = self._extract_skills(description) if description else []
            
            return JobData(
                title=title,
                company_name=company_name,
                location=location,
                description=description,
                salary_min=salary_info.get('min'),
                salary_max=salary_info.get('max'),
                salary_currency=salary_info.get('currency', 'USD'),
                salary_period=salary_info.get('period'),
                posted_date=posted_date,
                source="indeed",
                source_job_id=str(job_id) if job_id else None,
                source_url=job_url,
                skills_required=skills,
                is_remote=is_remote
            )
            
        except Exception as e:
            logger.debug(f"Error extracting job data: {e}")
            return None
    
    async def _extract_detailed_job_info(
        self,
        soup: BeautifulSoup,
        job_url: str
    ) -> Optional[JobData]:
        """Extract detailed job information from job detail page."""
        try:
            # Extract title
            title_elem = (
                soup.find('h1', class_='jobsearch-JobInfoHeader-title') or
                soup.find('h1', {'data-testid': 'job-title'}) or
                soup.find('h1')
            )
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Extract company
            company_elem = (
                soup.find('div', {'data-testid': 'inlineHeader-companyName'}) or
                soup.find('div', class_='jobsearch-CompanyInfoWithoutHeaderImage') or
                soup.find('span', class_='icl-u-lg-mr--sm')
            )
            company_name = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = (
                soup.find('div', {'data-testid': 'inlineHeader-companyLocation'}) or
                soup.find('div', class_='jobsearch-JobInfoHeader-subtitle') or
                soup.find('span', class_='jobsearch-JobMetadataHeader-iconLabel')
            )
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Extract full job description
            desc_elem = (
                soup.find('div', {'data-testid': 'jobsearch-jobDescriptionText'}) or
                soup.find('div', class_='jobsearch-jobDescriptionText') or
                soup.find('div', id='jobDescriptionText')
            )
            description = desc_elem.get_text(strip=True) if desc_elem else None
            
            # Extract salary
            salary_elem = (
                soup.find('span', class_='icl-u-xs-mr--xs') or
                soup.find('div', class_='jobsearch-JobMetadataHeader-item')
            )
            salary_info = {}
            if salary_elem and any(char.isdigit() for char in salary_elem.get_text()):
                salary_info = self._parse_salary(salary_elem.get_text(strip=True))
            
            # Extract job type and other metadata
            metadata_items = soup.find_all('div', class_='jobsearch-JobMetadataHeader-item')
            job_type = None
            
            for item in metadata_items:
                text = item.get_text(strip=True).lower()
                if any(jt in text for jt in ['full-time', 'part-time', 'contract', 'temporary']):
                    job_type = text.title()
                    break
            
            # Extract requirements if available
            requirements = None
            req_headers = soup.find_all(['h3', 'h4', 'strong'], string=re.compile('requirement|qualification', re.I))
            if req_headers:
                req_elem = req_headers[0].find_next(['div', 'ul', 'p'])
                if req_elem:
                    requirements = req_elem.get_text(strip=True)
            
            # Extract benefits
            benefits = []
            benefit_elem = soup.find('div', string=re.compile('benefit', re.I))
            if benefit_elem:
                benefit_list = benefit_elem.find_next(['ul', 'div'])
                if benefit_list:
                    benefits = [li.get_text(strip=True) for li in benefit_list.find_all('li')]
            
            # Determine if remote
            is_remote = self._is_remote_job(location, description)
            
            # Extract skills
            skills = self._extract_skills(f"{description} {requirements}" if requirements else description)
            
            return JobData(
                title=title,
                company_name=company_name,
                location=location,
                description=description,
                requirements=requirements,
                salary_min=salary_info.get('min'),
                salary_max=salary_info.get('max'),
                salary_currency=salary_info.get('currency', 'USD'),
                salary_period=salary_info.get('period'),
                job_type=job_type,
                source="indeed",
                source_url=job_url,
                skills_required=skills,
                benefits=benefits,
                is_remote=is_remote
            )
            
        except Exception as e:
            logger.error(f"Error extracting detailed job info: {e}")
            return None
    
    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Check if there's a next page in search results."""
        next_link = (
            soup.find('a', {'aria-label': 'Next Page'}) or
            soup.find('a', string=re.compile('next', re.I)) or
            soup.find('a', class_='pn')
        )
        return next_link is not None
    
    def _is_relevant_job(self, job_data: JobData) -> bool:
        """Check if job is relevant for MBA job hunters."""
        if not job_data.title or not job_data.description:
            return True  # Include if we can't determine relevance
        
        text_to_check = f"{job_data.title} {job_data.description}".lower()
        
        # Check for MBA-relevant keywords
        return any(keyword in text_to_check for keyword in self._mba_keywords)
    
    def _is_remote_job(self, location: Optional[str], description: Optional[str]) -> bool:
        """Determine if job is remote based on location and description."""
        if not location and not description:
            return False
        
        remote_indicators = ['remote', 'work from home', 'wfh', 'telecommute', 'anywhere']
        text_to_check = f"{location or ''} {description or ''}".lower()
        
        return any(indicator in text_to_check for indicator in remote_indicators)
    
    async def _make_http_request(self, url: str, **kwargs) -> httpx.Response:
        """Override to add Indeed-specific headers and user agent rotation."""
        # Rotate user agent
        import random
        user_agent = random.choice(self._user_agents)
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add referer for job detail pages
        if 'viewjob' in url:
            headers['Referer'] = 'https://www.indeed.com/'
        
        kwargs['headers'] = headers
        
        return await super()._make_http_request(url, **kwargs)