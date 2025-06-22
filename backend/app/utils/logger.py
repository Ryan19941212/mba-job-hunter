"""
Logging Configuration

Structured logging setup using structlog for consistent, JSON-formatted logs
throughout the MBA Job Hunter application.
"""

import logging
import sys
from typing import Any, Dict, Optional
from pathlib import Path

import structlog
from structlog.stdlib import LoggerFactory
from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

# Get settings
settings = get_settings()


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level and timestamp
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            
            # Add context
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            
            # JSON formatting for production, pretty for development
            structlog.dev.ConsoleRenderer() if settings.DEBUG 
            else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # File handler for persistent logging
    if not settings.DEBUG:
        file_handler = logging.FileHandler(logs_dir / "app.log")
        file_handler.setFormatter(
            jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s"
            )
        )
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


def log_function_call(func_name: str, **kwargs) -> None:
    """
    Log function call with parameters.
    
    Args:
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    logger = get_logger("function_calls")
    logger.info(
        "Function called",
        function=func_name,
        parameters=kwargs
    )


def log_api_request(
    method: str,
    path: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log API request.
    
    Args:
        method: HTTP method
        path: Request path
        user_id: User ID making the request
        ip_address: Client IP address
        **kwargs: Additional request data
    """
    logger = get_logger("api_requests")
    logger.info(
        "API request",
        method=method,
        path=path,
        user_id=user_id,
        ip_address=ip_address,
        **kwargs
    )


def log_scraping_activity(
    scraper_name: str,
    action: str,
    job_id: Optional[str] = None,
    url: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log scraping activity.
    
    Args:
        scraper_name: Name of the scraper
        action: Action being performed
        job_id: Job ID being processed
        url: URL being scraped
        **kwargs: Additional scraping data
    """
    logger = get_logger("scraping")
    logger.info(
        "Scraping activity",
        scraper=scraper_name,
        action=action,
        job_id=job_id,
        url=url,
        **kwargs
    )


def log_ai_analysis(
    analysis_type: str,
    job_id: Optional[int] = None,
    user_id: Optional[str] = None,
    model_used: Optional[str] = None,
    processing_time: Optional[float] = None,
    **kwargs
) -> None:
    """
    Log AI analysis activity.
    
    Args:
        analysis_type: Type of analysis performed
        job_id: Job ID being analyzed
        user_id: User ID requesting analysis
        model_used: AI model used for analysis
        processing_time: Time taken for analysis
        **kwargs: Additional analysis data
    """
    logger = get_logger("ai_analysis")
    logger.info(
        "AI analysis",
        analysis_type=analysis_type,
        job_id=job_id,
        user_id=user_id,
        model_used=model_used,
        processing_time_seconds=processing_time,
        **kwargs
    )


def log_database_operation(
    operation: str,
    table: str,
    record_id: Optional[int] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log database operation.
    
    Args:
        operation: Type of operation (create, read, update, delete)
        table: Database table involved
        record_id: Record ID being operated on
        user_id: User performing the operation
        **kwargs: Additional operation data
    """
    logger = get_logger("database")
    logger.info(
        "Database operation",
        operation=operation,
        table=table,
        record_id=record_id,
        user_id=user_id,
        **kwargs
    )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log error with context.
    
    Args:
        error: Exception that occurred
        context: Additional context about the error
        user_id: User ID associated with the error
        **kwargs: Additional error data
    """
    logger = get_logger("errors")
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        user_id=user_id,
        **kwargs,
        exc_info=True
    )


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "seconds",
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None:
    """
    Log performance metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        context: Additional context
        **kwargs: Additional metric data
    """
    logger = get_logger("performance")
    logger.info(
        "Performance metric",
        metric=metric_name,
        value=value,
        unit=unit,
        context=context or {},
        **kwargs
    )


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    **kwargs
) -> None:
    """
    Log security-related event.
    
    Args:
        event_type: Type of security event
        user_id: User ID involved
        ip_address: IP address involved
        success: Whether the event was successful
        **kwargs: Additional security data
    """
    logger = get_logger("security")
    
    log_level = "info" if success else "warning"
    getattr(logger, log_level)(
        "Security event",
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        success=success,
        **kwargs
    )


class ContextualLogger:
    """
    Logger with persistent context that can be used throughout a request/operation.
    """
    
    def __init__(self, base_logger: structlog.stdlib.BoundLogger, **context) -> None:
        """
        Initialize contextual logger.
        
        Args:
            base_logger: Base logger instance
            **context: Context to bind to all log messages
        """
        self._logger = base_logger.bind(**context)
        self._context = context
    
    def bind(self, **new_context) -> "ContextualLogger":
        """
        Bind additional context to the logger.
        
        Args:
            **new_context: Additional context to bind
            
        Returns:
            ContextualLogger: New logger with additional context
        """
        combined_context = {**self._context, **new_context}
        return ContextualLogger(self._logger, **combined_context)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._logger.critical(message, **kwargs)


def get_contextual_logger(name: str, **context) -> ContextualLogger:
    """
    Get a contextual logger with bound context.
    
    Args:
        name: Logger name
        **context: Context to bind to all log messages
        
    Returns:
        ContextualLogger: Logger with bound context
    """
    base_logger = get_logger(name)
    return ContextualLogger(base_logger, **context)


# Configure logging on import
configure_logging()