"""
Global Error Handling Middleware for MBA Job Hunter

Provides centralized error handling with:
- Structured error responses
- Sensitive information filtering
- Error logging and monitoring
- Environment-specific error details
- Integration with intelligent error recovery
"""

import traceback
import uuid
from typing import Dict, Any, Optional, Union
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError
import logging

from app.core.config import get_settings
from app.core.exceptions import BaseApplicationException, ErrorSeverity, ErrorCategory
from app.utils.logger import get_logger
from app.utils.metrics import production_metrics, SecurityEventTypes
from app.utils.error_handler import (
    user_friendly_error_handler, 
    handle_intelligent_error,
    create_error_context
)
from app.core.security import get_client_ip, security_audit_logger

logger = get_logger(__name__)
settings = get_settings()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware with intelligent error recovery.
    
    Features:
    - Structured error responses
    - Sensitive data filtering
    - Error monitoring and metrics
    - Intelligent error recovery
    - User-friendly error messages
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'credential',
            'authorization', 'cookie', 'session', 'api_key'
        }
        self.error_mappings = {
            # Map specific errors to intelligent error types
            'linkedin': 'linkedin_rate_limit',
            'notion': 'notion_api_error', 
            'openai': 'openai_quota_exceeded',
            'indeed': 'indeed_scraping_blocked',
            'database': 'database_connection_lost',
            'timeout': 'ai_analysis_timeout'
        }
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle requests with comprehensive error handling."""
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client information
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        user_id = getattr(request.state, 'user_id', None)
        
        # Create error context
        error_context = create_error_context(
            user_id=user_id,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Handle error with intelligent recovery
            return await self._handle_error(
                exc, 
                request, 
                error_context,
                request_id
            )
    
    async def _handle_error(
        self,
        exc: Exception,
        request: Request,
        error_context,
        request_id: str
    ) -> JSONResponse:
        """Handle errors with intelligent recovery and structured responses."""
        
        # Detect error type for intelligent handling
        error_type = self._detect_error_type(exc)
        
        # Try intelligent error handling first
        if error_type:
            try:
                recovery_result = handle_intelligent_error(
                    error_type, 
                    exc, 
                    error_context,
                    additional_data=self._extract_error_data(exc)
                )
                
                if recovery_result['recovery_attempted']:
                    # Log successful intelligent error handling
                    logger.info(
                        f"Intelligent error recovery: {error_type}",
                        extra={
                            'request_id': request_id,
                            'error_type': error_type,
                            'recovery_successful': recovery_result['recovery_successful'],
                            'user_message': recovery_result['user_message']
                        }
                    )
                    
                    # Record error recovery metrics
                    production_metrics.record_error_recovery(
                        error_type,
                        recovery_result.get('next_action', 'unknown'),
                        recovery_result['recovery_successful']
                    )
                    
                    # Return user-friendly response
                    return self._create_recovery_response(
                        recovery_result, 
                        request_id,
                        error_context
                    )
                    
            except Exception as recovery_error:
                logger.error(f"Error recovery failed: {recovery_error}")
        
        # Fallback to standard error handling
        return await self._handle_standard_error(exc, request, error_context, request_id)
    
    def _detect_error_type(self, exc: Exception) -> Optional[str]:
        """Detect error type for intelligent handling."""
        
        error_message = str(exc).lower()
        error_class = exc.__class__.__name__.lower()
        
        # Check for specific error patterns
        if any(term in error_message for term in ['linkedin', 'li_at']):
            return 'linkedin_rate_limit'
        elif any(term in error_message for term in ['notion', 'notion.com']):
            return 'notion_api_error'
        elif any(term in error_message for term in ['openai', 'quota', 'rate limit']):
            return 'openai_quota_exceeded'
        elif any(term in error_message for term in ['indeed', 'indeed.com']):
            return 'indeed_scraping_blocked'
        elif any(term in error_message for term in ['database', 'connection', 'sqlalchemy']):
            return 'database_connection_lost'
        elif any(term in error_message for term in ['timeout', 'timed out']):
            return 'ai_analysis_timeout'
        
        # Check error class patterns
        if 'timeout' in error_class:
            return 'ai_analysis_timeout'
        elif 'connection' in error_class:
            return 'database_connection_lost'
        
        return None
    
    def _extract_error_data(self, exc: Exception) -> Dict[str, Any]:
        """Extract additional data from exception for recovery."""
        data = {}
        
        if hasattr(exc, 'retry_after'):
            data['retry_delay'] = exc.retry_after
        
        if hasattr(exc, 'status_code'):
            data['status_code'] = exc.status_code
        
        if hasattr(exc, 'details'):
            data.update(exc.details)
        
        return data
    
    def _create_recovery_response(
        self,
        recovery_result: Dict[str, Any],
        request_id: str,
        error_context
    ) -> JSONResponse:
        """Create response for intelligent error recovery."""
        
        response_data = {
            "error": {
                "code": "INTELLIGENT_ERROR_RECOVERY",
                "message": recovery_result['user_message'],
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "recovery_info": {
                    "recovery_attempted": recovery_result['recovery_attempted'],
                    "recovery_successful": recovery_result['recovery_successful'],
                    "estimated_recovery_time": recovery_result.get('estimated_recovery_time'),
                    "alternative_options": recovery_result.get('alternative_options', [])
                }
            }
        }
        
        headers = {"X-Request-ID": request_id}
        
        # Add retry information if available
        if recovery_result.get('estimated_recovery_time'):
            headers["X-Recovery-Time"] = recovery_result['estimated_recovery_time']
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,  # Recovery successful
            content=response_data,
            headers=headers
        )
    
    async def _handle_standard_error(
        self,
        exc: Exception,
        request: Request,
        error_context,
        request_id: str
    ) -> JSONResponse:
        """Handle errors with standard error processing."""
        
        # Convert exception to structured error
        if isinstance(exc, BaseApplicationException):
            error_info = self._handle_application_error(exc)
        elif isinstance(exc, HTTPException):
            error_info = self._handle_http_error(exc)
        elif isinstance(exc, ValidationError):
            error_info = self._handle_validation_error(exc)
        elif isinstance(exc, (IntegrityError, OperationalError)):
            error_info = self._handle_database_error(exc)
        else:
            error_info = self._handle_unknown_error(exc)
        
        # Log error
        await self._log_error(exc, error_info, error_context, request_id)
        
        # Record metrics
        self._record_error_metrics(exc, error_info, error_context)
        
        # Create response
        return self._create_error_response(error_info, request_id)
    
    def _handle_application_error(self, exc: BaseApplicationException) -> Dict[str, Any]:
        """Handle custom application errors."""
        return {
            "error_code": exc.error_code,
            "message": exc.user_message,
            "category": exc.category.value,
            "severity": exc.severity.value,
            "http_status": exc.http_status,
            "details": self._filter_sensitive_data(exc.details),
            "suggested_action": exc.suggested_action,
            "retry_after": exc.retry_after
        }
    
    def _handle_http_error(self, exc: HTTPException) -> Dict[str, Any]:
        """Handle FastAPI HTTP errors."""
        return {
            "error_code": "HTTP_ERROR",
            "message": str(exc.detail),
            "category": ErrorCategory.SYSTEM.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "http_status": exc.status_code,
            "details": {},
            "suggested_action": "請檢查請求參數並重試"
        }
    
    def _handle_validation_error(self, exc: ValidationError) -> Dict[str, Any]:
        """Handle Pydantic validation errors."""
        field_errors = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            field_errors[field] = error["msg"]
        
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "輸入資料格式不正確",
            "category": ErrorCategory.VALIDATION.value,
            "severity": ErrorSeverity.LOW.value,
            "http_status": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "details": {"field_errors": field_errors},
            "suggested_action": "請檢查輸入格式並重試"
        }
    
    def _handle_database_error(self, exc: Exception) -> Dict[str, Any]:
        """Handle database errors."""
        if isinstance(exc, IntegrityError):
            return {
                "error_code": "DATABASE_INTEGRITY_ERROR",
                "message": "資料完整性錯誤",
                "category": ErrorCategory.DATABASE.value,
                "severity": ErrorSeverity.MEDIUM.value,
                "http_status": status.HTTP_400_BAD_REQUEST,
                "details": {},
                "suggested_action": "請檢查資料是否重複或格式錯誤"
            }
        else:
            return {
                "error_code": "DATABASE_ERROR",
                "message": "資料庫操作失敗",
                "category": ErrorCategory.DATABASE.value,
                "severity": ErrorSeverity.HIGH.value,
                "http_status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {},
                "suggested_action": "請稍後重試"
            }
    
    def _handle_unknown_error(self, exc: Exception) -> Dict[str, Any]:
        """Handle unknown errors."""
        return {
            "error_code": "INTERNAL_ERROR",
            "message": "系統發生未預期的錯誤",
            "category": ErrorCategory.SYSTEM.value,
            "severity": ErrorSeverity.HIGH.value,
            "http_status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "details": {} if settings.ENVIRONMENT == "production" else {"error_type": type(exc).__name__},
            "suggested_action": "請稍後重試或聯繫客服"
        }
    
    async def _log_error(
        self,
        exc: Exception,
        error_info: Dict[str, Any],
        error_context,
        request_id: str
    ) -> None:
        """Log error with appropriate level and context."""
        
        log_data = {
            'request_id': request_id,
            'error_code': error_info['error_code'],
            'category': error_info['category'],
            'severity': error_info['severity'],
            'http_status': error_info['http_status'],
            'client_ip': error_context.ip_address,
            'endpoint': error_context.endpoint,
            'method': error_context.method,
            'user_id': error_context.user_id
        }
        
        # Include technical details for non-production environments
        if settings.ENVIRONMENT != "production":
            log_data['exception_type'] = type(exc).__name__
            log_data['exception_message'] = str(exc)
            log_data['traceback'] = traceback.format_exc()
        
        # Log with appropriate level
        severity = error_info['severity']
        if severity == ErrorSeverity.CRITICAL.value:
            logger.critical(f"Critical error: {error_info['error_code']}", extra=log_data)
        elif severity == ErrorSeverity.HIGH.value:
            logger.error(f"High severity error: {error_info['error_code']}", extra=log_data)
        elif severity == ErrorSeverity.MEDIUM.value:
            logger.warning(f"Medium severity error: {error_info['error_code']}", extra=log_data)
        else:
            logger.info(f"Low severity error: {error_info['error_code']}", extra=log_data)
        
        # Log security events
        if error_info['category'] in [ErrorCategory.AUTHENTICATION.value, ErrorCategory.AUTHORIZATION.value]:
            security_audit_logger.log_security_threat(
                threat_type=error_info['error_code'],
                severity=severity,
                ip_address=error_context.ip_address,
                details=error_info['details'],
                user_identifier=error_context.user_id
            )
    
    def _record_error_metrics(
        self,
        exc: Exception,
        error_info: Dict[str, Any],
        error_context
    ) -> None:
        """Record error metrics for monitoring."""
        
        # Record application error
        production_metrics.record_application_error(
            error_type=error_info['error_code'],
            severity=error_info['severity'],
            component=error_context.endpoint or 'unknown'
        )
        
        # Record security events
        if error_info['category'] in [ErrorCategory.AUTHENTICATION.value, ErrorCategory.AUTHORIZATION.value]:
            production_metrics.record_security_event(
                event_type=error_info['error_code'],
                severity=error_info['severity']
            )
        
        # Record rate limit hits
        if error_info['category'] == ErrorCategory.RATE_LIMIT.value:
            production_metrics.record_rate_limit_hit(
                endpoint=error_context.endpoint or 'unknown',
                client_type='authenticated' if error_context.user_id else 'anonymous'
            )
    
    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out sensitive information from error details."""
        if not isinstance(data, dict):
            return data
        
        filtered = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive_data(value)
            elif isinstance(value, list):
                filtered[key] = [
                    self._filter_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value
        
        return filtered
    
    def _create_error_response(
        self,
        error_info: Dict[str, Any],
        request_id: str
    ) -> JSONResponse:
        """Create standardized error response."""
        
        response_data = {
            "error": {
                "code": error_info['error_code'],
                "message": error_info['message'],
                "category": error_info['category'],
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Add optional fields
        if error_info.get('details'):
            response_data["error"]["details"] = error_info['details']
        
        if error_info.get('suggested_action'):
            response_data["error"]["suggested_action"] = error_info['suggested_action']
        
        # Prepare headers
        headers = {"X-Request-ID": request_id}
        
        if error_info.get('retry_after'):
            headers["Retry-After"] = str(error_info['retry_after'])
        
        return JSONResponse(
            status_code=error_info['http_status'],
            content=response_data,
            headers=headers
        )


def setup_error_handling(app):
    """Setup global error handling middleware."""
    app.add_middleware(ErrorHandlingMiddleware)