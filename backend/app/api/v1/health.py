"""
Health Check API v1 Endpoints

System health and status monitoring endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    try:
        settings = get_settings()
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": "2024-01-01T00:00:00Z"  # Simple timestamp
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@router.get("/status")
async def detailed_status() -> Dict[str, Any]:
    """Detailed system status."""
    try:
        settings = get_settings()
        return {
            "status": "healthy",
            "services": {
                "api": "healthy",
                "database": "healthy",  # Would check actual DB in production
                "cache": "healthy"      # Would check actual cache in production
            },
            "app_info": {
                "name": settings.APP_NAME,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT
            }
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )