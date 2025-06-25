"""
Custom Exceptions for MBA Job Hunter

Business logic exceptions with user-friendly messages and proper error codes.
Designed for production use with comprehensive error tracking.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from fastapi import status


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    RATE_LIMIT = "rate_limit"
    CONFIGURATION = "configuration"


class BaseApplicationException(Exception):
    """
    Base exception for all application-specific errors.
    
    Provides structured error information for consistent error handling
    and user-friendly error responses.
    """
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        error_code: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        suggested_action: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.category = category
        self.severity = severity
        self.http_status = http_status
        self.details = details or {}
        self.suggested_action = suggested_action
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code,
            "message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "suggested_action": self.suggested_action,
            "retry_after": self.retry_after
        }


# Validation Exceptions
class ValidationException(BaseApplicationException):
    """Exception for input validation errors."""
    
    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            user_message="請檢查您的輸入資料",
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            http_status=status.HTTP_400_BAD_REQUEST,
            **kwargs
        )
        self.field_errors = field_errors or {}
        self.details.update({"field_errors": self.field_errors})


class InvalidJobDataException(ValidationException):
    """Exception for invalid job data."""
    
    def __init__(self, field: str, value: Any, **kwargs):
        super().__init__(
            message=f"Invalid job data: {field} = {value}",
            user_message=f"職缺資料 '{field}' 格式不正確",
            error_code="INVALID_JOB_DATA",
            field_errors={field: f"Invalid value: {value}"},
            **kwargs
        )


class InvalidSearchParametersException(ValidationException):
    """Exception for invalid search parameters."""
    
    def __init__(self, invalid_params: List[str], **kwargs):
        super().__init__(
            message=f"Invalid search parameters: {', '.join(invalid_params)}",
            user_message="搜尋參數格式不正確",
            error_code="INVALID_SEARCH_PARAMS",
            field_errors={param: "Invalid parameter" for param in invalid_params},
            suggested_action="請檢查搜尋條件並重試",
            **kwargs
        )


# Authentication and Authorization Exceptions
class AuthenticationException(BaseApplicationException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message=message,
            user_message="請先登入以使用此功能",
            error_code="AUTH_REQUIRED",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            http_status=status.HTTP_401_UNAUTHORIZED,
            suggested_action="請檢查您的登入狀態",
            **kwargs
        )


class InvalidTokenException(AuthenticationException):
    """Exception for invalid authentication tokens."""
    
    def __init__(self, **kwargs):
        super().__init__(
            message="Invalid or expired authentication token",
            user_message="登入已過期，請重新登入",
            error_code="INVALID_TOKEN",
            suggested_action="請重新登入",
            **kwargs
        )


class AuthorizationException(BaseApplicationException):
    """Exception for authorization errors."""
    
    def __init__(self, resource: str = "resource", **kwargs):
        super().__init__(
            message=f"Access denied to {resource}",
            user_message="您沒有權限執行此操作",
            error_code="ACCESS_DENIED",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            http_status=status.HTTP_403_FORBIDDEN,
            suggested_action="請聯繫管理員獲取權限",
            **kwargs
        )


# Resource Exceptions
class ResourceNotFoundException(BaseApplicationException):
    """Exception for resource not found errors."""
    
    def __init__(self, resource_type: str, resource_id: str = None, **kwargs):
        resource_desc = f"{resource_type}"
        if resource_id:
            resource_desc += f" (ID: {resource_id})"
        
        super().__init__(
            message=f"{resource_type} not found",
            user_message=f"找不到指定的{self._translate_resource_type(resource_type)}",
            error_code="RESOURCE_NOT_FOUND",
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.LOW,
            http_status=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id},
            suggested_action="請檢查資源ID或重新搜尋",
            **kwargs
        )
    
    def _translate_resource_type(self, resource_type: str) -> str:
        """Translate resource type to Chinese."""
        translations = {
            "job": "職缺",
            "company": "公司",
            "analysis": "分析結果",
            "user": "使用者",
            "profile": "個人檔案"
        }
        return translations.get(resource_type.lower(), resource_type)


class JobNotFoundException(ResourceNotFoundException):
    """Exception for job not found errors."""
    
    def __init__(self, job_id: str, **kwargs):
        super().__init__(
            resource_type="job",
            resource_id=job_id,
            user_message="找不到指定的職缺",
            **kwargs
        )


class CompanyNotFoundException(ResourceNotFoundException):
    """Exception for company not found errors."""
    
    def __init__(self, company_id: str, **kwargs):
        super().__init__(
            resource_type="company",
            resource_id=company_id,
            user_message="找不到指定的公司",
            **kwargs
        )


# Business Logic Exceptions
class BusinessLogicException(BaseApplicationException):
    """Exception for business logic violations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            user_message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            http_status=status.HTTP_400_BAD_REQUEST,
            **kwargs
        )


class DuplicateJobException(BusinessLogicException):
    """Exception for duplicate job entries."""
    
    def __init__(self, job_url: str, **kwargs):
        super().__init__(
            message=f"Job already exists: {job_url}",
            user_message="此職缺已存在於系統中",
            error_code="DUPLICATE_JOB",
            details={"job_url": job_url},
            suggested_action="請檢查是否為重複的職缺",
            **kwargs
        )


class InvalidJobStatusException(BusinessLogicException):
    """Exception for invalid job status transitions."""
    
    def __init__(self, current_status: str, target_status: str, **kwargs):
        super().__init__(
            message=f"Cannot change job status from {current_status} to {target_status}",
            user_message="無法更改職缺狀態",
            error_code="INVALID_STATUS_TRANSITION",
            details={"current_status": current_status, "target_status": target_status},
            **kwargs
        )


class ScrapingLimitExceededException(BusinessLogicException):
    """Exception for scraping limits exceeded."""
    
    def __init__(self, platform: str, limit: int, **kwargs):
        super().__init__(
            message=f"Scraping limit exceeded for {platform}: {limit}",
            user_message=f"{platform}搜尋次數已達每日上限",
            error_code="SCRAPING_LIMIT_EXCEEDED",
            details={"platform": platform, "limit": limit},
            suggested_action="請明天再試或聯繫客服",
            retry_after=86400,  # 24 hours
            **kwargs
        )


# External Service Exceptions
class ExternalServiceException(BaseApplicationException):
    """Exception for external service errors."""
    
    def __init__(
        self,
        service_name: str,
        message: str = "External service error",
        **kwargs
    ):
        super().__init__(
            message=f"{service_name}: {message}",
            user_message=f"外部服務暫時無法使用",
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service_name": service_name},
            suggested_action="請稍後再試",
            retry_after=300,  # 5 minutes
            **kwargs
        )


class LinkedInServiceException(ExternalServiceException):
    """Exception for LinkedIn API errors."""
    
    def __init__(self, error_details: Dict[str, Any] = None, **kwargs):
        super().__init__(
            service_name="LinkedIn",
            message="LinkedIn API error",
            user_message="LinkedIn連接暫時無法使用，已自動切換到其他來源",
            error_code="LINKEDIN_SERVICE_ERROR",
            details=error_details or {},
            suggested_action="系統已自動處理，無需額外操作",
            **kwargs
        )


class NotionServiceException(ExternalServiceException):
    """Exception for Notion API errors."""
    
    def __init__(self, error_details: Dict[str, Any] = None, **kwargs):
        super().__init__(
            service_name="Notion",
            message="Notion API error",
            user_message="Notion同步暫時無法使用，數據已保存在本地",
            error_code="NOTION_SERVICE_ERROR",
            details=error_details or {},
            suggested_action="稍後會自動重試同步",
            **kwargs
        )


class OpenAIServiceException(ExternalServiceException):
    """Exception for OpenAI API errors."""
    
    def __init__(self, error_details: Dict[str, Any] = None, **kwargs):
        super().__init__(
            service_name="OpenAI",
            message="OpenAI API error",
            user_message="AI分析服務暫時繁忙，為您提供基本分析結果",
            error_code="OPENAI_SERVICE_ERROR",
            details=error_details or {},
            suggested_action="稍後可重新分析獲得完整結果",
            **kwargs
        )


# Database Exceptions
class DatabaseException(BaseApplicationException):
    """Exception for database errors."""
    
    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(
            message=message,
            user_message="資料庫暫時無法訪問",
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            suggested_action="請稍後再試",
            **kwargs
        )


class DatabaseConnectionException(DatabaseException):
    """Exception for database connection errors."""
    
    def __init__(self, **kwargs):
        super().__init__(
            message="Database connection failed",
            user_message="資料庫連接失敗",
            error_code="DB_CONNECTION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            suggested_action="請稍後再試或聯繫技術支援",
            **kwargs
        )


class DatabaseTimeoutException(DatabaseException):
    """Exception for database timeout errors."""
    
    def __init__(self, operation: str, timeout: int, **kwargs):
        super().__init__(
            message=f"Database operation timed out: {operation} ({timeout}s)",
            user_message="資料庫操作超時",
            error_code="DB_TIMEOUT_ERROR",
            details={"operation": operation, "timeout": timeout},
            suggested_action="請稍後重試",
            **kwargs
        )


# Rate Limiting Exceptions
class RateLimitException(BaseApplicationException):
    """Exception for rate limiting errors."""
    
    def __init__(
        self,
        limit_type: str = "requests",
        retry_after: int = 60,
        **kwargs
    ):
        super().__init__(
            message=f"Rate limit exceeded: {limit_type}",
            user_message="請求次數過多，請稍後再試",
            error_code="RATE_LIMIT_EXCEEDED",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.LOW,
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"limit_type": limit_type},
            suggested_action=f"請等待{retry_after}秒後再試",
            retry_after=retry_after,
            **kwargs
        )


class APIRateLimitException(RateLimitException):
    """Exception for API rate limiting."""
    
    def __init__(self, endpoint: str, **kwargs):
        super().__init__(
            limit_type=f"API calls to {endpoint}",
            user_message="API呼叫次數過多，請稍後再試",
            error_code="API_RATE_LIMIT",
            details={"endpoint": endpoint},
            **kwargs
        )


class ScrapingRateLimitException(RateLimitException):
    """Exception for scraping rate limiting."""
    
    def __init__(self, platform: str, **kwargs):
        super().__init__(
            limit_type=f"scraping from {platform}",
            user_message=f"{platform}搜尋頻率過高，請稍後再試",
            error_code="SCRAPING_RATE_LIMIT",
            details={"platform": platform},
            retry_after=300,  # 5 minutes
            **kwargs
        )


# Configuration Exceptions
class ConfigurationException(BaseApplicationException):
    """Exception for configuration errors."""
    
    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            message=f"Configuration error: {config_key}",
            user_message="系統配置錯誤",
            error_code="CONFIG_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"config_key": config_key},
            suggested_action="請聯繫技術支援",
            **kwargs
        )


class MissingEnvironmentVariableException(ConfigurationException):
    """Exception for missing environment variables."""
    
    def __init__(self, var_name: str, **kwargs):
        super().__init__(
            config_key=var_name,
            message=f"Missing required environment variable: {var_name}",
            user_message="系統配置不完整",
            error_code="MISSING_ENV_VAR",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


# Network Exceptions
class NetworkException(BaseApplicationException):
    """Exception for network-related errors."""
    
    def __init__(self, message: str = "Network error", **kwargs):
        super().__init__(
            message=message,
            user_message="網路連接異常",
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            http_status=status.HTTP_502_BAD_GATEWAY,
            suggested_action="請檢查網路連接並重試",
            **kwargs
        )


class TimeoutException(NetworkException):
    """Exception for timeout errors."""
    
    def __init__(self, operation: str, timeout: int, **kwargs):
        super().__init__(
            message=f"Operation timed out: {operation} ({timeout}s)",
            user_message="操作超時",
            error_code="TIMEOUT_ERROR",
            details={"operation": operation, "timeout": timeout},
            suggested_action="請重試，如問題持續請聯繫客服",
            **kwargs
        )


class ConnectionException(NetworkException):
    """Exception for connection errors."""
    
    def __init__(self, host: str, **kwargs):
        super().__init__(
            message=f"Connection failed to {host}",
            user_message="連接失敗",
            error_code="CONNECTION_ERROR",
            details={"host": host},
            **kwargs
        )


# AI and Analysis Exceptions
class AIAnalysisException(BaseApplicationException):
    """Exception for AI analysis errors."""
    
    def __init__(self, analysis_type: str, **kwargs):
        super().__init__(
            message=f"AI analysis failed: {analysis_type}",
            user_message="AI分析暫時無法使用",
            error_code="AI_ANALYSIS_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            details={"analysis_type": analysis_type},
            suggested_action="已為您提供基本分析結果",
            **kwargs
        )


class InsufficientDataException(BusinessLogicException):
    """Exception for insufficient data errors."""
    
    def __init__(self, data_type: str, minimum_required: int, **kwargs):
        super().__init__(
            message=f"Insufficient {data_type} data (minimum: {minimum_required})",
            user_message=f"數據不足，無法進行{data_type}分析",
            error_code="INSUFFICIENT_DATA",
            details={"data_type": data_type, "minimum_required": minimum_required},
            suggested_action="請增加更多數據或調整分析參數",
            **kwargs
        )