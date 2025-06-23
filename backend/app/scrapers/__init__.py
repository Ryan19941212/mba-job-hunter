"""
Job Scrapers Package

Contains web scrapers for various job boards including Indeed, LinkedIn, and Levels.fyi.
Each scraper implements the base scraper interface for consistent data extraction.
"""

from .base import BaseScraper, JobData, ScrapingConfig, ScraperType, ScraperManager
from .indeed import IndeedScraper
from .utils import (
    job_deduplicator,
    robots_checker,
    location_normalizer,
    salary_parser,
    skill_extractor,
    load_scraper_config,
    validate_job_data,
    calculate_job_relevance_score
)

__all__ = [
    # Base classes
    'BaseScraper',
    'JobData', 
    'ScrapingConfig',
    'ScraperType',
    'ScraperManager',
    
    # Scrapers
    'IndeedScraper',
    
    # Utilities
    'job_deduplicator',
    'robots_checker',
    'location_normalizer',
    'salary_parser',
    'skill_extractor',
    'load_scraper_config',
    'validate_job_data',
    'calculate_job_relevance_score'
]