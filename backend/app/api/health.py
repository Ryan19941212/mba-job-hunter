"""
Health Check API Endpoints

Provides health check and system status endpoints
for monitoring and load balancer health checks.
"""

from typing import Dict, Any
from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db, cache_helper
from app.core.config import get_settings
from app.core.database import db_manager
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get settings
settings = get_settings()

# Create router
router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict[str, Any]: Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Detailed health check with dependency status.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Detailed health status
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # Check Redis connection
    try:
        redis_client = db_manager.redis
        await redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # Check external API keys (without exposing them)
    api_keys_status = []
    
    if settings.OPENAI_API_KEY:
        api_keys_status.append("openai")
    if settings.ANTHROPIC_API_KEY:
        api_keys_status.append("anthropic")
    if settings.NOTION_API_KEY:
        api_keys_status.append("notion")
    if settings.INDEED_API_KEY:
        api_keys_status.append("indeed")
    
    health_status["checks"]["api_keys"] = {
        "status": "healthy" if api_keys_status else "warning",
        "configured": api_keys_status,
        "message": f"Configured API keys: {', '.join(api_keys_status) if api_keys_status else 'none'}"
    }
    
    return health_status


@router.get("/health/ready", response_model=Dict[str, str])
async def readiness_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Kubernetes readiness probe endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, str]: Readiness status
        
    Raises:
        HTTPException: If system is not ready
    """
    try:
        # Check database
        await db.execute(text("SELECT 1"))
        
        # Check Redis
        redis_client = db_manager.redis
        await redis_client.ping()
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/health/live", response_model=Dict[str, str])
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.
    
    Returns:
        Dict[str, str]: Liveness status
    """
    # Simple liveness check - if we can respond, we're alive
    return {"status": "alive"}


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Basic application metrics endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Application metrics
    """
    # Check cache for metrics
    cache_key = "app_metrics"
    cached_metrics = await cache_helper.get_cached_response(cache_key)
    
    if cached_metrics:
        import json
        return json.loads(cached_metrics)
    
    try:
        # Get database metrics
        db_metrics = await _get_database_metrics(db)
        
        # Get application metrics
        app_metrics = {
            "uptime_seconds": _get_uptime_seconds(),
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        metrics = {
            "application": app_metrics,
            "database": db_metrics
        }
        
        # Cache metrics for 30 seconds
        import json
        await cache_helper.set_cached_response(
            cache_key, 
            json.dumps(metrics, default=str), 
            expire_seconds=30
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect metrics"
        )


async def _get_database_metrics(db: AsyncSession) -> Dict[str, Any]:
    """
    Get database-related metrics.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Database metrics
    """
    try:
        # Basic database queries to get counts
        # Note: These would need to be implemented based on your actual models
        
        metrics = {
            "connection_status": "connected",
            "tables": {
                "jobs": 0,  # await db.scalar(select(func.count(Job.id)))
                "companies": 0,  # await db.scalar(select(func.count(Company.id)))
                "analyses": 0,  # await db.scalar(select(func.count(Analysis.id)))
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Database metrics collection failed: {e}")
        return {
            "connection_status": "error",
            "error": str(e)
        }


def _get_uptime_seconds() -> float:
    """
    Get application uptime in seconds.
    
    Returns:
        float: Uptime in seconds
    """
    # This is a simple implementation
    # In a real application, you'd track the start time
    import time
    return time.time() - _get_uptime_seconds._start_time if hasattr(_get_uptime_seconds, '_start_time') else 0.0


# Initialize start time
_get_uptime_seconds._start_time = datetime.utcnow().timestamp()