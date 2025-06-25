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
from app.core.container import init_container, shutdown_container
from app.api.v1 import jobs_router, analysis_router, health_router, metrics_router
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
    
    # Initialize dependency injection container
    try:
        await init_container()
        logger.info("Application container initialized successfully")
    except Exception as e:
        logger.error(f"Container initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MBA Job Hunter API...")
    try:
        await shutdown_container()
        logger.info("Application container shutdown complete")
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
app.include_router(health_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(metrics_router)




# Remove old background tasks function since it's now handled by container


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