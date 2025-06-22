"""
FastAPI Main Application

Entry point for the MBA Job Hunter API server.
Configures routing, middleware, and application lifecycle events.
"""

from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import asyncio

from app.core.config import get_settings
from app.core.database import init_db
from app.api import health, jobs, analysis
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get application settings
settings = get_settings()

# Create FastAPI application instance
app = FastAPI(
    title="MBA Job Hunter API",
    description="Comprehensive job hunting platform for MBA graduates and professionals",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup."""
    logger.info("Starting MBA Job Hunter API...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized successfully")
    
    # Start background tasks
    asyncio.create_task(start_background_tasks())
    logger.info("Background tasks started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on application shutdown."""
    logger.info("Shutting down MBA Job Hunter API...")


async def start_background_tasks() -> None:
    """Start background tasks for job scraping and analysis."""
    from app.services.job_matcher import JobMatcherService
    from app.scrapers.base import ScraperManager
    
    # Initialize services
    scraper_manager = ScraperManager()
    job_matcher = JobMatcherService()
    
    # Start periodic tasks
    if settings.ENABLE_BACKGROUND_SCRAPING:
        asyncio.create_task(scraper_manager.run_periodic_scraping())
        logger.info("Periodic job scraping enabled")
    
    if settings.ENABLE_AUTO_MATCHING:
        asyncio.create_task(job_matcher.run_periodic_matching())
        logger.info("Automatic job matching enabled")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "message": "MBA Job Hunter API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/api/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )