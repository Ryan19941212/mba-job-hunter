"""
FastAPI Main Application

Entry point for the MBA Job Hunter API server.
Configures routing, middleware, and application lifecycle events.
"""

from typing import Dict, Any
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import asyncio

from app.core.config import get_settings
from app.core.database import init_db, db_manager
from app.api import health, jobs, analysis
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get application settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MBA Job Hunter API...")
    
    # Try to initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}. Continuing without database...")
    
    # Start background tasks if enabled (only if database is available)
    if settings.ENABLE_BACKGROUND_SCRAPING or settings.ENABLE_AUTO_MATCHING:
        try:
            asyncio.create_task(start_background_tasks())
            logger.info("Background tasks started")
        except Exception as e:
            logger.warning(f"Failed to start background tasks: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MBA Job Hunter API...")
    try:
        await db_manager.close_connections()
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")
    logger.info("Application shutdown complete")


# Create FastAPI application instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Comprehensive job hunting platform for MBA graduates and professionals with intelligent matching and automated analysis",
    version=settings.VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.get_cors_methods_list(),
    allow_headers=settings.get_cors_headers_list(),
)

# Add trusted host middleware for production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.get_cors_origins_list()
    )

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])




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


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc)
            }
        )


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "message": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs_url": "/api/docs" if settings.DEBUG else None,
        "health_url": "/api/v1/health"
    }


@app.get("/api")
async def api_info() -> Dict[str, Any]:
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "health": "/api/v1/health",
            "jobs": "/api/v1/jobs",
            "analysis": "/api/v1/analysis",
            "docs": "/api/docs" if settings.DEBUG else None
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )