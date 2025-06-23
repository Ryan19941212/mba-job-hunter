"""
Scraper Utilities

Common utilities and helper functions for job scrapers.
"""

import re
import json
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urljoin
import hashlib

import httpx
from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobDeduplicator:
    """
    Utility class for detecting and removing duplicate job postings.
    """
    
    def __init__(self):
        self._seen_jobs: Set[str] = set()
        self._job_hashes: Dict[str, str] = {}
    
    def is_duplicate(self, job_data: Dict[str, Any]) -> bool:
        """
        Check if job is a duplicate based on title, company, and location.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            bool: True if job is a duplicate
        """
        # Create a hash from key fields
        key_fields = [
            str(job_data.get('title', '')).lower().strip(),
            str(job_data.get('company_name', '')).lower().strip(),
            str(job_data.get('location', '')).lower().strip()
        ]
        
        job_key = '|'.join(key_fields)
        job_hash = hashlib.md5(job_key.encode()).hexdigest()
        
        if job_hash in self._seen_jobs:
            return True
        
        self._seen_jobs.add(job_hash)
        self._job_hashes[job_hash] = job_key
        return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        return {
            "unique_jobs": len(self._seen_jobs),
            "total_processed": len(self._job_hashes)
        }


class RobotsTxtChecker:
    """
    Utility for checking robots.txt compliance.
    """
    
    def __init__(self):
        self._robots_cache: Dict[str, Dict] = {}
    
    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string
            
        Returns:
            bool: True if fetching is allowed
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self._robots_cache:
                await self._fetch_robots_txt(base_url)
            
            robots_data = self._robots_cache.get(base_url, {})
            
            # If no robots.txt or error fetching, allow by default
            if not robots_data:
                return True
            
            # Check disallowed paths
            disallowed = robots_data.get('disallow', [])
            for pattern in disallowed:
                if pattern and parsed_url.path.startswith(pattern):
                    logger.debug(f"URL {url} disallowed by robots.txt")
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Error checking robots.txt for {url}: {e}")
            return True  # Allow by default on error
    
    async def _fetch_robots_txt(self, base_url: str) -> None:
        """Fetch and parse robots.txt for a domain."""
        robots_url = urljoin(base_url, '/robots.txt')
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(robots_url, timeout=10)
                
                if response.status_code == 200:
                    self._robots_cache[base_url] = self._parse_robots_txt(response.text)
                else:
                    self._robots_cache[base_url] = {}
                    
        except Exception as e:
            logger.debug(f"Error fetching robots.txt from {robots_url}: {e}")
            self._robots_cache[base_url] = {}
    
    def _parse_robots_txt(self, content: str) -> Dict[str, List[str]]:
        """Parse robots.txt content."""
        robots_data = {'disallow': [], 'allow': []}
        current_user_agent = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.lower().startswith('user-agent:'):
                current_user_agent = line.split(':', 1)[1].strip()
            elif line.lower().startswith('disallow:') and current_user_agent in ['*', 'googlebot']:
                path = line.split(':', 1)[1].strip()
                if path:
                    robots_data['disallow'].append(path)
            elif line.lower().startswith('allow:') and current_user_agent in ['*', 'googlebot']:
                path = line.split(':', 1)[1].strip()
                if path:
                    robots_data['allow'].append(path)
        
        return robots_data


class LocationNormalizer:
    """
    Utility for normalizing and standardizing location strings.
    """
    
    # Common location mappings
    LOCATION_MAPPINGS = {
        'sf': 'San Francisco',
        'la': 'Los Angeles',
        'nyc': 'New York',
        'ny': 'New York',
        'dc': 'Washington DC',
        'chi': 'Chicago',
        'philly': 'Philadelphia',
        'boston': 'Boston',
        'seattle': 'Seattle',
        'austin': 'Austin',
        'denver': 'Denver',
        'atlanta': 'Atlanta',
        'miami': 'Miami',
        'remote': 'Remote',
        'work from home': 'Remote',
        'wfh': 'Remote',
        'telecommute': 'Remote'
    }
    
    # State abbreviations
    STATE_ABBREVS = {
        'ca': 'California', 'ny': 'New York', 'tx': 'Texas',
        'fl': 'Florida', 'il': 'Illinois', 'pa': 'Pennsylvania',
        'oh': 'Ohio', 'mi': 'Michigan', 'ga': 'Georgia',
        'nc': 'North Carolina', 'nj': 'New Jersey', 'va': 'Virginia',
        'wa': 'Washington', 'ma': 'Massachusetts', 'in': 'Indiana',
        'az': 'Arizona', 'tn': 'Tennessee', 'mo': 'Missouri',
        'md': 'Maryland', 'wi': 'Wisconsin', 'mn': 'Minnesota',
        'co': 'Colorado', 'al': 'Alabama', 'la': 'Louisiana',
        'ky': 'Kentucky', 'or': 'Oregon', 'ok': 'Oklahoma',
        'ct': 'Connecticut', 'ut': 'Utah', 'ia': 'Iowa',
        'nv': 'Nevada', 'ar': 'Arkansas', 'ms': 'Mississippi',
        'ks': 'Kansas', 'ne': 'Nebraska', 'nm': 'New Mexico',
        'id': 'Idaho', 'wv': 'West Virginia', 'nh': 'New Hampshire',
        'hi': 'Hawaii', 'me': 'Maine', 'ri': 'Rhode Island',
        'mt': 'Montana', 'de': 'Delaware', 'sd': 'South Dakota',
        'ak': 'Alaska', 'nd': 'North Dakota', 'dc': 'Washington DC',
        'vt': 'Vermont', 'wy': 'Wyoming'
    }
    
    @classmethod
    def normalize_location(cls, location: Optional[str]) -> Optional[str]:
        """
        Normalize location string to standard format.
        
        Args:
            location: Raw location string
            
        Returns:
            Optional[str]: Normalized location or None
        """
        if not location:
            return None
        
        # Clean and standardize
        location = location.strip().lower()
        location = re.sub(r'\s+', ' ', location)  # Remove extra spaces
        location = re.sub(r'[^\w\s,.-]', '', location)  # Remove special chars
        
        # Check direct mappings
        if location in cls.LOCATION_MAPPINGS:
            return cls.LOCATION_MAPPINGS[location]
        
        # Extract city, state pattern
        parts = [part.strip() for part in location.split(',')]
        
        if len(parts) >= 2:
            city = parts[0].title()
            state_part = parts[1].strip()
            
            # Check if state is abbreviated
            if state_part in cls.STATE_ABBREVS:
                state = cls.STATE_ABBREVS[state_part]
                return f"{city}, {state}"
            else:
                return f"{city}, {state_part.title()}"
        
        # Single location (might be city or state)
        location_title = location.title()
        
        # Check if it's a state abbreviation
        if location in cls.STATE_ABBREVS:
            return cls.STATE_ABBREVS[location]
        
        return location_title
    
    @classmethod
    def is_remote_location(cls, location: Optional[str]) -> bool:
        """Check if location indicates remote work."""
        if not location:
            return False
        
        remote_indicators = [
            'remote', 'work from home', 'wfh', 'telecommute',
            'anywhere', 'distributed', 'virtual'
        ]
        
        return any(indicator in location.lower() for indicator in remote_indicators)


class SalaryParser:
    """
    Advanced salary parsing utility with support for multiple formats.
    """
    
    CURRENCY_SYMBOLS = {
        '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY',
        'usd': 'USD', 'eur': 'EUR', 'gbp': 'GBP', 'jpy': 'JPY'
    }
    
    PERIOD_INDICATORS = {
        'hour': 'hourly', 'hr': 'hourly', 'hourly': 'hourly',
        'year': 'annual', 'annual': 'annual', 'yearly': 'annual',
        'month': 'monthly', 'monthly': 'monthly',
        'week': 'weekly', 'weekly': 'weekly'
    }
    
    @classmethod
    def parse_salary(cls, salary_text: str) -> Dict[str, Any]:
        """
        Parse salary information from text with advanced pattern matching.
        
        Args:
            salary_text: Raw salary text
            
        Returns:
            Dict[str, Any]: Parsed salary information
        """
        result = {
            'min': None,
            'max': None,
            'currency': 'USD',
            'period': None,
            'raw_text': salary_text
        }
        
        if not salary_text:
            return result
        
        # Clean the text
        text = salary_text.strip().lower()
        text = re.sub(r'[^\w\s$€£¥,.-]', ' ', text)  # Keep basic punctuation
        
        # Extract currency
        for symbol, currency in cls.CURRENCY_SYMBOLS.items():
            if symbol in text:
                result['currency'] = currency
                break
        
        # Extract period
        for indicator, period in cls.PERIOD_INDICATORS.items():
            if indicator in text:
                result['period'] = period
                break
        
        # If no period specified, try to infer from salary range
        if not result['period']:
            # Extract numbers first to help determine period
            numbers = re.findall(r'[\d,]+(?:\.\d+)?', text.replace(',', ''))
            numbers = [float(n) for n in numbers if n]
            
            if numbers:
                avg_salary = sum(numbers) / len(numbers)
                if avg_salary < 200:  # Likely hourly
                    result['period'] = 'hourly'
                elif avg_salary < 10000:  # Likely monthly
                    result['period'] = 'monthly'
                else:  # Likely annual
                    result['period'] = 'annual'
        
        # First, handle K/k suffix (e.g., $120K -> $120000, 200K -> 200000)
        text_normalized = re.sub(r'(\d+)k\b', r'\g<1>000', text, flags=re.IGNORECASE)
        
        # Extract all numbers with potential commas
        number_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        
        # Try range patterns first
        range_patterns = [
            r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[-–—]\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',  # $120,000 - $150,000
            r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+to\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',      # $120,000 to $150,000
        ]
        
        range_found = False
        for pattern in range_patterns:
            match = re.search(pattern, text_normalized, re.IGNORECASE)
            if match:
                min_val = float(match.group(1).replace(',', ''))
                max_val = float(match.group(2).replace(',', ''))
                result['min'] = min_val
                result['max'] = max_val
                range_found = True
                break
        
        if not range_found:
            # Look for single number patterns
            if re.search(r'up\s+to', text, re.IGNORECASE):
                # "Up to $150,000"
                match = re.search(r'up\s+to\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text_normalized, re.IGNORECASE)
                if match:
                    result['max'] = float(match.group(1).replace(',', ''))
            elif re.search(r'(from|starting)', text, re.IGNORECASE):
                # "From $90,000" or "Starting at $90,000"
                match = re.search(r'(?:from|starting)\s+(?:at\s+)?\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text_normalized, re.IGNORECASE)
                if match:
                    result['min'] = float(match.group(1).replace(',', ''))
            else:
                # General single number
                match = re.search(number_pattern, text_normalized)
                if match:
                    salary_num = float(match.group(1).replace(',', ''))
                    result['min'] = salary_num
        
        # Convert hourly to annual if needed
        if result['period'] == 'hourly' and (result['min'] or result['max']):
            if result['min']:
                result['min'] = result['min'] * 40 * 52  # 40 hours/week, 52 weeks/year
            if result['max']:
                result['max'] = result['max'] * 40 * 52
            result['period'] = 'annual'
        
        return result


class SkillExtractor:
    """
    Enhanced skill extraction utility with MBA-focused skill recognition.
    """
    
    # Comprehensive skill patterns for MBA roles
    SKILL_PATTERNS = {
        'technical': [
            r'\b(SQL|MySQL|PostgreSQL|Oracle)\b',
            r'\b(Python|R|SAS|SPSS)\b',
            r'\b(Excel|VBA|Macros)\b',
            r'\b(PowerBI|Power BI|Tableau|Looker|QlikView)\b',
            r'\b(Salesforce|HubSpot|Marketo)\b',
            r'\b(SAP|Oracle|NetSuite)\b',
            r'\b(AWS|Azure|GCP|Google Cloud)\b',
            r'\b(Jira|Confluence|Asana|Monday\.com)\b'
        ],
        'business': [
            r'\b(MBA|Master of Business Administration)\b',
            r'\b(Strategy|Strategic Planning|Business Strategy)\b',
            r'\b(Business Analysis|Business Analytics)\b',
            r'\b(Project Management|Program Management)\b',
            r'\b(Product Management|Product Marketing)\b',
            r'\b(Operations Management|Process Improvement)\b',
            r'\b(Financial Modeling|Financial Analysis)\b',
            r'\b(Market Research|Competitive Analysis)\b',
            r'\b(Change Management|Organizational Development)\b'
        ],
        'leadership': [
            r'\b(Leadership|Team Leadership|People Management)\b',
            r'\b(Communication|Presentation|Public Speaking)\b',
            r'\b(Negotiation|Stakeholder Management)\b',
            r'\b(Cross-functional|Cross functional)\b',
            r'\b(Mentoring|Coaching|Training)\b'
        ],
        'methodologies': [
            r'\b(Agile|Scrum|Kanban|Lean)\b',
            r'\b(Six Sigma|Lean Six Sigma)\b',
            r'\b(Design Thinking|Human-Centered Design)\b',
            r'\b(OKRs|KPIs|Metrics)\b',
            r'\b(A/B Testing|Experimentation)\b'
        ],
        'industry': [
            r'\b(Consulting|Management Consulting)\b',
            r'\b(Investment Banking|Private Equity|Venture Capital)\b',
            r'\b(Healthcare|Pharmaceutical|Biotech)\b',
            r'\b(Technology|Software|SaaS)\b',
            r'\b(Financial Services|Banking|Insurance)\b',
            r'\b(Retail|E-commerce|Consumer Goods)\b',
            r'\b(Manufacturing|Supply Chain|Logistics)\b'
        ]
    }
    
    @classmethod
    def extract_skills(cls, text: str, max_skills: int = 25) -> List[str]:
        """
        Extract skills from job description text.
        
        Args:
            text: Job description or requirements text
            max_skills: Maximum number of skills to return
            
        Returns:
            List[str]: Extracted skills
        """
        if not text:
            return []
        
        skills = set()
        text_lower = text.lower()
        
        # Extract skills by category
        for category, patterns in cls.SKILL_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    skill = match.group(0).strip()
                    if skill and len(skill) > 1:
                        skills.add(skill)
        
        # Sort by relevance (frequency in text) and return top skills
        skill_list = list(skills)
        skill_counts = [(skill, text_lower.count(skill.lower())) for skill in skill_list]
        skill_counts.sort(key=lambda x: x[1], reverse=True)
        
        return [skill for skill, _ in skill_counts[:max_skills]]


# Global utility instances
job_deduplicator = JobDeduplicator()
robots_checker = RobotsTxtChecker()
location_normalizer = LocationNormalizer()
salary_parser = SalaryParser()
skill_extractor = SkillExtractor()


def load_scraper_config() -> Dict[str, Any]:
    """Load scraper configuration from JSON file."""
    config_path = Path("config/scraper_settings.json")
    
    if not config_path.exists():
        logger.warning("Scraper config file not found, using defaults")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading scraper config: {e}")
        return {}


async def validate_job_data(job_data: Dict[str, Any]) -> bool:
    """
    Validate job data meets minimum quality requirements.
    
    Args:
        job_data: Job data dictionary
        
    Returns:
        bool: True if job data is valid
    """
    config = load_scraper_config()
    quality_settings = config.get('data_quality', {})
    
    # Check required fields
    required_fields = quality_settings.get('required_fields', ['title', 'company_name'])
    for field in required_fields:
        if not job_data.get(field):
            logger.debug(f"Job data missing required field: {field}")
            return False
    
    # Check minimum lengths
    title = job_data.get('title', '')
    if len(title) < quality_settings.get('min_title_length', 3):
        logger.debug(f"Job title too short: {title}")
        return False
    
    description = job_data.get('description', '')
    if len(description) < quality_settings.get('min_description_length', 50):
        logger.debug(f"Job description too short: {len(description)} chars")
        return False
    
    return True


def calculate_job_relevance_score(job_data: Dict[str, Any]) -> float:
    """
    Calculate relevance score for MBA job hunters.
    
    Args:
        job_data: Job data dictionary
        
    Returns:
        float: Relevance score between 0.0 and 1.0
    """
    score = 0.0
    max_score = 0.0
    
    title = str(job_data.get('title', '')).lower()
    description = str(job_data.get('description', '')).lower()
    company = str(job_data.get('company_name', '')).lower()
    
    text_to_analyze = f"{title} {description} {company}"
    
    # Title relevance (40% weight)
    mba_title_keywords = [
        'manager', 'analyst', 'consultant', 'director', 'strategy',
        'product', 'business', 'operations', 'marketing', 'finance'
    ]
    
    title_matches = sum(1 for keyword in mba_title_keywords if keyword in title)
    title_score = min(title_matches / 3, 1.0) * 0.4
    score += title_score
    max_score += 0.4
    
    # Skills relevance (30% weight)
    skills = job_data.get('skills_required', [])
    if skills:
        mba_skills = ['mba', 'strategy', 'analytics', 'leadership', 'project management']
        skill_matches = sum(1 for skill in skills if any(mba_skill in skill.lower() for mba_skill in mba_skills))
        skill_score = min(skill_matches / 5, 1.0) * 0.3
        score += skill_score
    max_score += 0.3
    
    # Salary relevance (20% weight) - MBA roles typically have higher salaries
    salary_min = job_data.get('salary_min')
    if salary_min and salary_min >= 60000:  # Minimum MBA salary threshold
        salary_score = min((salary_min - 60000) / 140000, 1.0) * 0.2  # Scale up to 200k
        score += salary_score
    max_score += 0.2
    
    # Company type relevance (10% weight)
    prestigious_companies = [
        'google', 'microsoft', 'amazon', 'apple', 'meta', 'tesla',
        'mckinsey', 'bcg', 'bain', 'deloitte', 'pwc', 'accenture',
        'goldman', 'morgan', 'jpmorgan', 'blackstone', 'kkr'
    ]
    
    company_score = 0.1 if any(comp in company for comp in prestigious_companies) else 0.05
    score += company_score
    max_score += 0.1
    
    return score / max_score if max_score > 0 else 0.0