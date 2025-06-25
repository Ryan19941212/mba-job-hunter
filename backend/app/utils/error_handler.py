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


class UserFriendlyErrorHandler(ErrorHandler):
    """Enhanced error handler focused on user experience and intelligent recovery."""
    
    def __init__(self):
        super().__init__()
        self.error_mappings = {
            'linkedin_rate_limit': {
                'user_message': 'LinkedIn搜索暫時受限，已自動切換到Indeed獲取更多職缺',
                'recovery_action': 'auto_fallback_indeed',
                'business_impact': 'maintain_user_experience',
                'internal_action': 'increment_fallback_counter'
            },
            'notion_api_error': {
                'user_message': 'Notion同步暫時無法使用，數據已保存將稍後重試',
                'recovery_action': 'queue_for_retry',
                'business_impact': 'user_retention_risk',
                'internal_action': 'alert_support_team'
            },
            'openai_quota_exceeded': {
                'user_message': 'AI分析服務暫時繁忙，為您提供基礎匹配結果',
                'recovery_action': 'fallback_basic_matching',
                'business_impact': 'reduced_value_delivery',
                'internal_action': 'escalate_to_ops'
            },
            'indeed_scraping_blocked': {
                'user_message': '職缺獲取遇到暫時限制，正在嘗試其他數據源',
                'recovery_action': 'rotate_user_agent',
                'business_impact': 'maintain_user_experience',
                'internal_action': 'update_scraping_strategy'
            },
            'database_connection_lost': {
                'user_message': '數據暫時無法訪問，正在重新連接中',
                'recovery_action': 'retry_with_backoff',
                'business_impact': 'service_disruption',
                'internal_action': 'alert_infrastructure_team'
            },
            'ai_analysis_timeout': {
                'user_message': 'AI分析正在處理中，將於完成後通知您',
                'recovery_action': 'queue_for_background_processing',
                'business_impact': 'delayed_value_delivery',
                'internal_action': 'scale_processing_resources'
            }
        }
        self.recovery_metrics = {
            'fallback_success_count': 0,
            'retry_success_count': 0,
            'user_satisfaction_maintained': 0
        }
    
    def handle_intelligent_error(
        self,
        error_type: str,
        original_error: Exception,
        context: Optional[ErrorContext] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle errors with intelligent recovery and user-focused messaging.
        
        Args:
            error_type: Type of error from error_mappings
            original_error: The original exception
            context: Error context
            additional_data: Additional context data
            
        Returns:
            Dict containing user message, recovery status, and next actions
        """
        if error_type not in self.error_mappings:
            # Fallback to standard error handling
            error_info = self.handle_error(original_error, context)
            return {
                'user_message': error_info.user_message,
                'recovery_attempted': False,
                'business_impact': 'unknown',
                'next_action': 'standard_error_flow'
            }
        
        mapping = self.error_mappings[error_type]
        
        # Execute recovery action
        recovery_result = self._execute_recovery_action(
            mapping['recovery_action'],
            original_error,
            additional_data or {}
        )
        
        # Execute internal action
        self._execute_internal_action(
            mapping['internal_action'],
            error_type,
            original_error,
            context
        )
        
        # Track business impact
        self._track_business_impact(mapping['business_impact'], error_type)
        
        # Log the intelligent error handling
        self._log_intelligent_error(error_type, mapping, recovery_result, original_error)
        
        return {
            'user_message': mapping['user_message'],
            'recovery_attempted': True,
            'recovery_successful': recovery_result['success'],
            'business_impact': mapping['business_impact'],
            'next_action': recovery_result.get('next_action', 'continue'),
            'estimated_recovery_time': recovery_result.get('estimated_time'),
            'alternative_options': recovery_result.get('alternatives', [])
        }
    
    def _execute_recovery_action(
        self,
        action: str,
        original_error: Exception,
        additional_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute specific recovery actions based on error type."""
        
        recovery_actions = {
            'auto_fallback_indeed': self._fallback_to_indeed,
            'queue_for_retry': self._queue_for_retry,
            'fallback_basic_matching': self._fallback_basic_matching,
            'rotate_user_agent': self._rotate_user_agent,
            'retry_with_backoff': self._retry_with_backoff,
            'queue_for_background_processing': self._queue_background_processing
        }
        
        if action in recovery_actions:
            try:
                result = recovery_actions[action](original_error, additional_data)
                self.recovery_metrics[f'{action.split("_")[0]}_success_count'] += 1
                return result
            except Exception as recovery_error:
                logger.error(f"Recovery action {action} failed: {recovery_error}")
                return {
                    'success': False,
                    'error': str(recovery_error),
                    'next_action': 'manual_intervention_required'
                }
        
        return {'success': False, 'error': 'Unknown recovery action'}
    
    def _fallback_to_indeed(self, error: Exception, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback from LinkedIn to Indeed scraping."""
        return {
            'success': True,
            'next_action': 'switch_to_indeed_scraper',
            'estimated_time': '30秒',
            'alternatives': ['手動搜索LinkedIn', '等待限制解除後重試']
        }
    
    def _queue_for_retry(self, error: Exception, data: Dict[str, Any]) -> Dict[str, Any]:
        """Queue operation for retry with exponential backoff."""
        retry_delay = data.get('retry_delay', 300)  # 5 minutes default
        return {
            'success': True,
            'next_action': 'add_to_retry_queue',
            'estimated_time': f'{retry_delay // 60}分鐘',
            'retry_delay': retry_delay
        }
    
    def _fallback_basic_matching(self, error: Exception, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to basic keyword matching without AI."""
        return {
            'success': True,
            'next_action': 'use_basic_matching_algorithm',
            'estimated_time': '即時',
            'alternatives': ['等待AI服務恢復', '手動篩選職缺']
        }
    
    def _rotate_user_agent(self, error: Exception, data: Dict[str, Any]) -> Dict[str, Any]:
        """Rotate user agent and retry scraping."""
        return {
            'success': True,
            'next_action': 'update_scraper_headers',
            'estimated_time': '10秒',
            'alternatives': ['使用代理服務', '降低請求頻率']
        }
    
    def _retry_with_backoff(self, error: Exception, data: Dict[str, Any]) -> Dict[str, Any]:
        """Retry with exponential backoff."""
        return {
            'success': True,
            'next_action': 'schedule_retry',
            'estimated_time': '1-5分鐘',
            'retry_attempts': data.get('retry_count', 0) + 1
        }
    
    def _queue_background_processing(self, error: Exception, data: Dict[str, Any]) -> Dict[str, Any]:
        """Queue for background processing."""
        return {
            'success': True,
            'next_action': 'add_to_background_queue',
            'estimated_time': '5-10分鐘',
            'alternatives': ['簡化分析結果', '手動分析職缺']
        }
    
    def _execute_internal_action(
        self,
        action: str,
        error_type: str,
        original_error: Exception,
        context: Optional[ErrorContext]
    ) -> None:
        """Execute internal actions for monitoring and alerting."""
        
        internal_actions = {
            'increment_fallback_counter': lambda: self._increment_counter(f'{error_type}_fallback'),
            'alert_support_team': lambda: self._send_alert('support', error_type, original_error),
            'escalate_to_ops': lambda: self._escalate_to_ops(error_type, original_error),
            'update_scraping_strategy': lambda: self._update_scraping_strategy(error_type),
            'alert_infrastructure_team': lambda: self._send_alert('infrastructure', error_type, original_error),
            'scale_processing_resources': lambda: self._request_resource_scaling(error_type)
        }
        
        if action in internal_actions:
            try:
                internal_actions[action]()
            except Exception as e:
                logger.error(f"Internal action {action} failed: {e}")
    
    def _increment_counter(self, counter_name: str) -> None:
        """Increment error counter for monitoring."""
        self.error_counts[counter_name] = self.error_counts.get(counter_name, 0) + 1
    
    def _send_alert(self, team: str, error_type: str, error: Exception) -> None:
        """Send alert to specific team."""
        logger.warning(f"Alert sent to {team} team for {error_type}: {str(error)}")
        # In production: integrate with Slack, PagerDuty, etc.
    
    def _escalate_to_ops(self, error_type: str, error: Exception) -> None:
        """Escalate critical issues to operations team."""
        logger.error(f"Escalating {error_type} to operations: {str(error)}")
        # In production: create incident ticket, notify on-call engineer
    
    def _update_scraping_strategy(self, error_type: str) -> None:
        """Update scraping strategy based on error patterns."""
        logger.info(f"Updating scraping strategy due to {error_type}")
        # In production: update scraper configuration, rotate proxies
    
    def _request_resource_scaling(self, error_type: str) -> None:
        """Request additional processing resources."""
        logger.info(f"Requesting resource scaling for {error_type}")
        # In production: trigger auto-scaling, request additional compute
    
    def _track_business_impact(self, impact: str, error_type: str) -> None:
        """Track business impact of errors."""
        impact_metrics = {
            'maintain_user_experience': 'user_satisfaction_maintained',
            'user_retention_risk': 'user_retention_risk_count',
            'reduced_value_delivery': 'reduced_value_count',
            'service_disruption': 'service_disruption_count',
            'delayed_value_delivery': 'delayed_delivery_count'
        }
        
        if impact in impact_metrics:
            metric_name = impact_metrics[impact]
            self.recovery_metrics[metric_name] = self.recovery_metrics.get(metric_name, 0) + 1
    
    def _log_intelligent_error(
        self,
        error_type: str,
        mapping: Dict[str, str],
        recovery_result: Dict[str, Any],
        original_error: Exception
    ) -> None:
        """Log intelligent error handling with context."""
        log_data = {
            'error_type': error_type,
            'user_message': mapping['user_message'],
            'recovery_action': mapping['recovery_action'],
            'business_impact': mapping['business_impact'],
            'recovery_successful': recovery_result.get('success', False),
            'estimated_recovery_time': recovery_result.get('estimated_time'),
            'original_error': str(original_error)
        }
        
        logger.info(f"Intelligent error handling for {error_type}", extra=log_data)
    
    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get recovery and user experience metrics."""
        return {
            'recovery_metrics': self.recovery_metrics.copy(),
            'error_statistics': self.get_error_statistics(),
            'user_experience_score': self._calculate_ux_score()
        }
    
    def _calculate_ux_score(self) -> float:
        """Calculate user experience score based on error handling."""
        total_errors = sum(self.error_counts.values())
        if total_errors == 0:
            return 100.0
        
        successful_recoveries = sum([
            self.recovery_metrics.get('fallback_success_count', 0),
            self.recovery_metrics.get('retry_success_count', 0),
            self.recovery_metrics.get('user_satisfaction_maintained', 0)
        ])
        
        ux_score = (successful_recoveries / total_errors) * 100
        return min(100.0, max(0.0, ux_score))


# Global error handler instances
error_handler = ErrorHandler()
user_friendly_error_handler = UserFriendlyErrorHandler()


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


def handle_intelligent_error(
    error_type: str,
    original_error: Exception,
    context: Optional[ErrorContext] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for intelligent error handling with user experience focus.
    
    Args:
        error_type: Type of error from error_mappings
        original_error: The original exception
        context: Optional error context
        additional_data: Additional context data
        
    Returns:
        Dict containing user message, recovery status, and next actions
    """
    return user_friendly_error_handler.handle_intelligent_error(
        error_type, original_error, context, additional_data
    )


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