"""
Enhanced Error Handling System

Comprehensive error handling utilities with classification, logging,
monitoring integration, and user-friendly error responses.
"""

import traceback
import sys
from typing import Dict, Any, Optional, Type, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification."""
    
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for errors."""
    
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Structured error information."""
    
    error_code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    user_message: str
    technical_details: Optional[str] = None
    suggested_action: Optional[str] = None
    context: Optional[ErrorContext] = None
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    retry_after: Optional[int] = None


class ApplicationError(Exception):
    """Base application exception with enhanced error information."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        technical_details: Optional[str] = None,
        suggested_action: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.error_info = ErrorInfo(
            error_code=error_code,
            message=message,
            category=category,
            severity=severity,
            user_message=user_message or message,
            technical_details=technical_details,
            suggested_action=suggested_action,
            context=context,
            http_status=http_status,
            retry_after=retry_after
        )


class ValidationError(ApplicationError):
    """Validation error with field-level details."""
    
    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            http_status=status.HTTP_400_BAD_REQUEST,
            **kwargs
        )
        self.field_errors = field_errors or {}


class AuthenticationError(ApplicationError):
    """Authentication-related errors."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            user_message="Please log in to access this resource",
            suggested_action="Verify your credentials and try again",
            http_status=status.HTTP_401_UNAUTHORIZED,
            **kwargs
        )


class AuthorizationError(ApplicationError):
    """Authorization-related errors."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHZ_ERROR",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            user_message="You don't have permission to access this resource",
            suggested_action="Contact your administrator for access",
            http_status=status.HTTP_403_FORBIDDEN,
            **kwargs
        )


class NotFoundError(ApplicationError):
    """Resource not found errors."""
    
    def __init__(self, resource: str = "Resource", **kwargs):
        message = f"{resource} not found"
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.LOW,
            user_message=f"The requested {resource.lower()} could not be found",
            suggested_action="Check the ID or try searching for the resource",
            http_status=status.HTTP_404_NOT_FOUND,
            **kwargs
        )


class BusinessLogicError(ApplicationError):
    """Business logic validation errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="BUSINESS_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            http_status=status.HTTP_400_BAD_REQUEST,
            **kwargs
        )


class ExternalServiceError(ApplicationError):
    """External service integration errors."""
    
    def __init__(
        self,
        service_name: str,
        message: str = "External service unavailable",
        **kwargs
    ):
        super().__init__(
            message=f"{service_name}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            user_message="A required service is temporarily unavailable",
            suggested_action="Please try again in a few minutes",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            retry_after=300,  # 5 minutes
            **kwargs
        )


class DatabaseError(ApplicationError):
    """Database operation errors."""
    
    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            user_message="A database error occurred while processing your request",
            suggested_action="Please try again or contact support if the issue persists",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            **kwargs
        )


class RateLimitError(ApplicationError):
    """Rate limiting errors."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.LOW,
            user_message="Too many requests. Please slow down and try again later",
            suggested_action=f"Wait {retry_after} seconds before making another request",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            retry_after=retry_after,
            **kwargs
        )


class ErrorHandler:
    """Centralized error handling and logging."""
    
    def __init__(self):
        self.error_counts = {}
        self.error_patterns = {}
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None
    ) -> ErrorInfo:
        """
        Handle any exception and return structured error information.
        
        Args:
            error: The exception to handle
            context: Additional context information
            
        Returns:
            ErrorInfo: Structured error information
        """
        try:
            # Track error occurrence
            self._track_error(error)
            
            # Convert to structured error
            if isinstance(error, ApplicationError):
                error_info = error.error_info
                if context and not error_info.context:
                    error_info.context = context
            else:
                error_info = self._convert_standard_error(error, context)
            
            # Log the error
            self._log_error(error_info, error)
            
            # Send to monitoring (if configured)
            self._send_to_monitoring(error_info, error)
            
            return error_info
            
        except Exception as e:
            # Fallback error handling
            logger.critical(f"Error in error handler: {e}", exc_info=True)
            return self._create_fallback_error(str(e))
    
    def create_error_response(self, error_info: ErrorInfo) -> JSONResponse:
        """
        Create HTTP error response from error information.
        
        Args:
            error_info: Structured error information
            
        Returns:
            JSONResponse: HTTP error response
        """
        response_data = {
            "error": {
                "code": error_info.error_code,
                "message": error_info.user_message,
                "category": error_info.category.value,
                "timestamp": error_info.context.timestamp.isoformat() if error_info.context else datetime.utcnow().isoformat()
            }
        }
        
        # Add suggested action if available
        if error_info.suggested_action:
            response_data["error"]["suggested_action"] = error_info.suggested_action
        
        # Add field errors for validation errors
        if hasattr(error_info, 'field_errors') and error_info.field_errors:
            response_data["error"]["field_errors"] = error_info.field_errors
        
        # Add retry information for rate limiting
        headers = {}
        if error_info.retry_after:
            headers["Retry-After"] = str(error_info.retry_after)
        
        return JSONResponse(
            status_code=error_info.http_status,
            content=response_data,
            headers=headers
        )
    
    def _convert_standard_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None
    ) -> ErrorInfo:
        """Convert standard Python exceptions to ErrorInfo."""
        
        # HTTPException (FastAPI)
        if isinstance(error, HTTPException):
            return ErrorInfo(
                error_code="HTTP_ERROR",
                message=str(error.detail),
                category=self._categorize_http_error(error.status_code),
                severity=self._determine_severity(error.status_code),
                user_message=str(error.detail),
                context=context,
                http_status=error.status_code
            )
        
        # Pydantic ValidationError
        if isinstance(error, ValidationError):
            field_errors = {}
            for error_detail in error.errors():
                field = ".".join(str(loc) for loc in error_detail["loc"])
                field_errors[field] = error_detail["msg"]
            
            return ErrorInfo(
                error_code="VALIDATION_ERROR",
                message="Validation failed",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                user_message="Please check your input and try again",
                technical_details=str(error),
                context=context,
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        # ValueError
        if isinstance(error, ValueError):
            return ErrorInfo(
                error_code="VALUE_ERROR",
                message=str(error),
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                user_message="Invalid input provided",
                technical_details=str(error),
                context=context,
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generic exception
        return ErrorInfo(
            error_code="INTERNAL_ERROR",
            message=str(error),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            user_message="An unexpected error occurred",
            technical_details=traceback.format_exc(),
            suggested_action="Please try again or contact support",
            context=context,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def _categorize_http_error(self, status_code: int) -> ErrorCategory:
        """Categorize HTTP errors."""
        if status_code == 401:
            return ErrorCategory.AUTHENTICATION
        elif status_code == 403:
            return ErrorCategory.AUTHORIZATION
        elif status_code == 404:
            return ErrorCategory.NOT_FOUND
        elif status_code == 422:
            return ErrorCategory.VALIDATION
        elif status_code == 429:
            return ErrorCategory.SYSTEM
        elif 400 <= status_code < 500:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.SYSTEM
    
    def _determine_severity(self, status_code: int) -> ErrorSeverity:
        """Determine error severity from HTTP status code."""
        if status_code >= 500:
            return ErrorSeverity.HIGH
        elif status_code == 429:
            return ErrorSeverity.MEDIUM
        elif status_code >= 400:
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.LOW
    
    def _track_error(self, error: Exception) -> None:
        """Track error occurrence for monitoring."""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Track error patterns (simplified)
        error_signature = f"{error_type}:{str(error)[:100]}"
        self.error_patterns[error_signature] = self.error_patterns.get(error_signature, 0) + 1
    
    def _log_error(self, error_info: ErrorInfo, original_error: Exception) -> None:
        """Log error with appropriate level."""
        log_data = {
            "error_code": error_info.error_code,
            "category": error_info.category.value,
            "severity": error_info.severity.value,
            "message": error_info.message,
            "user_message": error_info.user_message
        }
        
        if error_info.context:
            log_data.update({
                "user_id": error_info.context.user_id,
                "request_id": error_info.context.request_id,
                "endpoint": error_info.context.endpoint,
                "method": error_info.context.method
            })
        
        # Log with appropriate level based on severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {error_info.message}", extra=log_data, exc_info=original_error)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {error_info.message}", extra=log_data, exc_info=original_error)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {error_info.message}", extra=log_data)
        else:
            logger.info(f"Low severity error: {error_info.message}", extra=log_data)
    
    def _send_to_monitoring(self, error_info: ErrorInfo, original_error: Exception) -> None:
        """Send error to monitoring system (placeholder)."""
        # In production, integrate with monitoring services like:
        # - Sentry
        # - Datadog
        # - New Relic
        # - Custom metrics endpoints
        
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            # Send alert for high-severity errors
            logger.debug(f"Would send alert for {error_info.severity.value} error: {error_info.error_code}")
    
    def _create_fallback_error(self, message: str) -> ErrorInfo:
        """Create fallback error when error handling fails."""
        return ErrorInfo(
            error_code="HANDLER_ERROR",
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            user_message="A critical system error occurred",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "error_counts": self.error_counts.copy(),
            "error_patterns": dict(list(self.error_patterns.items())[-10:]),  # Last 10
            "total_errors": sum(self.error_counts.values()),
            "unique_error_types": len(self.error_counts)
        }


# Global error handler instance
error_handler = ErrorHandler()


def handle_error(error: Exception, context: Optional[ErrorContext] = None) -> JSONResponse:
    """
    Convenience function for handling errors.
    
    Args:
        error: Exception to handle
        context: Optional error context
        
    Returns:
        JSONResponse: HTTP error response
    """
    error_info = error_handler.handle_error(error, context)
    return error_handler.create_error_response(error_info)


def create_error_context(
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    **kwargs
) -> ErrorContext:
    """
    Create error context from request information.
    
    Args:
        user_id: User identifier
        request_id: Request identifier
        endpoint: API endpoint
        method: HTTP method
        **kwargs: Additional context data
        
    Returns:
        ErrorContext: Error context object
    """
    return ErrorContext(
        user_id=user_id,
        request_id=request_id,
        endpoint=endpoint,
        method=method,
        additional_data=kwargs
    )