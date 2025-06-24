"""
API v1 Package

Contains all version 1 API endpoints for the MBA Job Hunter application.
"""

from .jobs import router as jobs_router
from .analysis import router as analysis_router
from .health import router as health_router

__all__ = [
    "jobs_router",
    "analysis_router", 
    "health_router"
]