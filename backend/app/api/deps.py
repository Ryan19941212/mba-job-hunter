"""
API Dependencies

Common dependencies used across API endpoints including
database sessions, authentication, pagination, and validation.
"""

from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session, cache_manager
from app.core.security import get_current_user, get_optional_current_user, rate_limiter
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class Pagination:
    """Pagination parameters for API endpoints."""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Page size"),
        sort_by: Optional[str] = Query(None, description="Sort field"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
    ) -> None:
        """
        Initialize pagination parameters.
        
        Args:
            page: Page number (1-based)
            size: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
        """
        self.page = page
        self.size = size
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.offset = (page - 1) * size
        self.limit = size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pagination to dictionary."""
        return {
            "page": self.page,
            "size": self.size,
            "offset": self.offset,
            "limit": self.limit,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order
        }


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.
    
    Yields:
        AsyncSession: Database session
    """
    async for session in get_db_session():
        yield session


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current active user dependency.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Dict[str, Any]: Current user information
        
    Raises:
        HTTPException: If user is inactive
    """
    # Here you would typically check if user is active in database
    # For now, we'll assume all users are active
    return current_user


async def get_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
) -> Pagination:
    """
    Pagination dependency.
    
    Args:
        page: Page number
        size: Page size
        sort_by: Sort field
        sort_order: Sort order
        
    Returns:
        Pagination: Pagination parameters
    """
    return Pagination(page=page, size=size, sort_by=sort_by, sort_order=sort_order)


class RateLimitChecker:
    """Rate limiting dependency."""
    
    def __init__(self, requests_per_minute: int = 60) -> None:
        """
        Initialize rate limit checker.
        
        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
    
    async def __call__(self, request: Request) -> None:
        """
        Check rate limit for request.
        
        Args:
            request: FastAPI request object
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Use IP address as identifier
        client_ip = request.client.host if request.client else "unknown"
        
        if not rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )


# Common rate limit dependency
check_rate_limit = RateLimitChecker()


class CacheHelper:
    """Cache helper for API endpoints."""
    
    @staticmethod
    async def get_cached_response(cache_key: str) -> Optional[str]:
        """
        Get cached response.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Optional[str]: Cached response or None
        """
        try:
            return await cache_manager.get(cache_key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set_cached_response(
        cache_key: str, 
        response: str, 
        expire_seconds: int = 300
    ) -> bool:
        """
        Set cached response.
        
        Args:
            cache_key: Cache key
            response: Response to cache
            expire_seconds: Expiration time in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            return await cache_manager.set(cache_key, response, expire_seconds)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    def generate_cache_key(prefix: str, **kwargs) -> str:
        """
        Generate cache key from parameters.
        
        Args:
            prefix: Cache key prefix
            **kwargs: Parameters to include in key
            
        Returns:
            str: Generated cache key
        """
        parts = [prefix]
        for key, value in sorted(kwargs.items()):
            if value is not None:
                parts.append(f"{key}:{value}")
        return ":".join(parts)


# Global cache helper instance
cache_helper = CacheHelper()


class ValidationHelper:
    """Common validation utilities."""
    
    @staticmethod
    def validate_job_search_params(
        query: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate job search parameters.
        
        Args:
            query: Search query
            location: Job location
            company: Company name
            salary_min: Minimum salary
            salary_max: Maximum salary
            
        Returns:
            Dict[str, Any]: Validated parameters
            
        Raises:
            HTTPException: If validation fails
        """
        if salary_min is not None and salary_min < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum salary must be non-negative"
            )
        
        if salary_max is not None and salary_max < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum salary must be non-negative"
            )
        
        if (salary_min is not None and salary_max is not None 
            and salary_min > salary_max):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum salary cannot be greater than maximum salary"
            )
        
        return {
            "query": query.strip() if query else None,
            "location": location.strip() if location else None,
            "company": company.strip() if company else None,
            "salary_min": salary_min,
            "salary_max": salary_max
        }
    
    @staticmethod
    def validate_date_range(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Validate date range parameters.
        
        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            Dict[str, Optional[str]]: Validated dates
            
        Raises:
            HTTPException: If validation fails
        """
        from datetime import datetime
        
        try:
            parsed_start = None
            parsed_end = None
            
            if start_date:
                parsed_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            if end_date:
                parsed_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            if parsed_start and parsed_end and parsed_start > parsed_end:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start date cannot be after end date"
                )
            
            return {
                "start_date": start_date,
                "end_date": end_date
            }
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {e}"
            )


# Global validation helper instance
validation_helper = ValidationHelper()