"""
Application Configuration

Centralized configuration management using Pydantic settings.
Handles environment variables, secrets, and application settings.
"""

from typing import List, Optional, Any, Dict
from functools import lru_cache
import json
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl
from pydantic import PostgresDsn, RedisDsn


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "MBA Job Hunter"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(False, env="DEBUG")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    TESTING: bool = Field(False, env="TESTING")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(5, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: RedisDsn = Field(..., env="REDIS_URL")
    REDIS_EXPIRE_SECONDS: int = Field(3600, env="REDIS_EXPIRE_SECONDS")
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    NOTION_API_KEY: Optional[str] = Field(None, env="NOTION_API_KEY")
    INDEED_API_KEY: Optional[str] = Field(None, env="INDEED_API_KEY")
    
    # External Services
    NOTION_DATABASE_ID: Optional[str] = Field(None, env="NOTION_DATABASE_ID")
    WEBHOOK_URL: Optional[str] = Field(None, env="WEBHOOK_URL")
    
    # Scraping Configuration
    ENABLE_BACKGROUND_SCRAPING: bool = Field(True, env="ENABLE_BACKGROUND_SCRAPING")
    SCRAPE_INTERVAL_HOURS: int = Field(24, env="SCRAPE_INTERVAL_HOURS")
    MAX_PAGES_PER_SCRAPER: int = Field(10, env="MAX_PAGES_PER_SCRAPER")
    REQUEST_DELAY_SECONDS: float = Field(2.0, env="REQUEST_DELAY_SECONDS")
    MAX_CONCURRENT_REQUESTS: int = Field(10, env="MAX_CONCURRENT_REQUESTS")
    
    # Job Matching
    ENABLE_AUTO_MATCHING: bool = Field(True, env="ENABLE_AUTO_MATCHING")
    SIMILARITY_THRESHOLD: float = Field(0.8, env="SIMILARITY_THRESHOLD")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    
    # CORS - simplified to avoid parsing issues
    CORS_ORIGINS: str = Field("http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000", env="CORS_ORIGINS")
    CORS_CREDENTIALS: bool = Field(True, env="CORS_CREDENTIALS")
    CORS_METHODS: str = Field("*", env="CORS_METHODS")
    CORS_HEADERS: str = Field("*", env="CORS_HEADERS")
    
    # LinkedIn Credentials (for scraping)
    LINKEDIN_EMAIL: Optional[str] = Field(None, env="LINKEDIN_EMAIL")
    LINKEDIN_PASSWORD: Optional[str] = Field(None, env="LINKEDIN_PASSWORD")
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    def get_cors_methods_list(self) -> List[str]:
        """Get CORS methods as a list."""
        if self.CORS_METHODS == "*":
            return ["*"]
        return [method.strip() for method in self.CORS_METHODS.split(",")]
    
    def get_cors_headers_list(self) -> List[str]:
        """Get CORS headers as a list."""
        if self.CORS_HEADERS == "*":
            return ["*"]
        return [header.strip() for header in self.CORS_HEADERS.split(",")]
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def load_keywords_config() -> Dict[str, List[str]]:
    """Load job search keywords from configuration file."""
    config_path = Path("config/keywords.json")
    
    if not config_path.exists():
        # Return default keywords if file doesn't exist
        return {
            "job_titles": ["Product Manager", "Consultant", "Business Analyst"],
            "skills": ["MBA", "Strategy", "Analytics"],
            "companies": ["Google", "McKinsey", "Goldman Sachs"],
            "locations": ["San Francisco", "New York", "Remote"],
            "exclude_keywords": ["Intern", "Entry Level"]
        }
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise ValueError(f"Error loading keywords configuration: {e}")


def load_user_profile() -> Optional[Dict[str, Any]]:
    """Load user profile configuration."""
    config_path = Path("config/user_profile.json")
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def load_app_settings() -> Dict[str, Any]:
    """Load additional application settings from JSON."""
    config_path = Path("config/settings.json")
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


# Global settings instance - removed to avoid circular import