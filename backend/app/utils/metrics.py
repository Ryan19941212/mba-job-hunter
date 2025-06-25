"""
Comprehensive monitoring system for MBA Job Hunter.
Focuses on product metrics for business insights.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from typing import Optional
import time
from functools import wraps
from contextlib import contextmanager


class JobHunterMetrics:
    """
    Central metrics collection for MBA Job Hunter.
    Tracks business-critical metrics for product insights.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics with optional custom registry."""
        self.registry = registry or CollectorRegistry()
        
        # Job search metrics - core business functionality
        self.job_searches_total = Counter(
            'job_searches_total',
            'Total number of job searches performed',
            ['platform', 'success'],
            registry=self.registry
        )
        
        # User action tracking - product engagement
        self.user_actions_total = Counter(
            'user_actions_total',
            'Total user actions across the platform',
            ['action_type'],
            registry=self.registry
        )
        
        # API performance - technical health affecting user experience
        self.api_response_seconds = Histogram(
            'api_response_seconds',
            'API response time in seconds',
            ['endpoint'],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        # AI job matching quality - core value proposition
        self.job_match_quality = Histogram(
            'job_match_quality_score',
            'Distribution of AI job match quality scores',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )
        
        # Notion integration health - critical integration
        self.notion_sync_success = Counter(
            'notion_sync_operations_total',
            'Notion synchronization operations',
            ['operation_type', 'status'],
            registry=self.registry
        )
        
        # Additional business metrics
        self.active_job_applications = Gauge(
            'active_job_applications',
            'Current number of active job applications being tracked',
            registry=self.registry
        )
        
        self.jobs_processed_total = Counter(
            'jobs_processed_total',
            'Total jobs processed through the system',
            ['source', 'status'],
            registry=self.registry
        )
        
        self.user_sessions_total = Counter(
            'user_sessions_total',
            'Total user sessions',
            ['session_type'],
            registry=self.registry
        )
    
    def record_job_search(self, platform: str, success: bool):
        """Record a job search attempt."""
        self.job_searches_total.labels(
            platform=platform,
            success='success' if success else 'failure'
        ).inc()
    
    def record_user_action(self, action_type: str):
        """Record user action for engagement tracking."""
        self.user_actions_total.labels(action_type=action_type).inc()
    
    def record_job_match_score(self, score: float):
        """Record AI job match quality score."""
        self.job_match_quality.observe(score)
    
    def record_notion_operation(self, operation_type: str, success: bool):
        """Record Notion sync operation result."""
        status = 'success' if success else 'failure'
        self.notion_sync_success.labels(
            operation_type=operation_type,
            status=status
        ).inc()
    
    def record_job_processed(self, source: str, status: str):
        """Record job processing result."""
        self.jobs_processed_total.labels(source=source, status=status).inc()
    
    def record_user_session(self, session_type: str = 'web'):
        """Record user session start."""
        self.user_sessions_total.labels(session_type=session_type).inc()
    
    def set_active_applications(self, count: int):
        """Update active job applications count."""
        self.active_job_applications.set(count)
    
    @contextmanager
    def time_api_call(self, endpoint: str):
        """Context manager to time API calls."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.api_response_seconds.labels(endpoint=endpoint).observe(duration)
    
    def api_timer(self, endpoint: str):
        """Decorator to time API endpoint calls."""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.time_api_call(endpoint):
                    return await func(*args, **kwargs)
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.time_api_call(endpoint):
                    return func(*args, **kwargs)
                    
            return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
        return decorator
    
    def get_metrics(self) -> str:
        """Get current metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics instance
metrics = JobHunterMetrics()


# Common action types for consistency
class ActionTypes:
    """Standard action types for user_actions_total metric."""
    JOB_SEARCH = 'job_search'
    JOB_VIEW = 'job_view'
    JOB_SAVE = 'job_save'
    JOB_APPLY = 'job_apply'
    PROFILE_UPDATE = 'profile_update'
    SETTINGS_CHANGE = 'settings_change'
    EXPORT_DATA = 'export_data'
    FILTER_JOBS = 'filter_jobs'
    SORT_JOBS = 'sort_jobs'
    NOTION_SYNC = 'notion_sync'


# Common operation types for Notion
class NotionOperations:
    """Standard operation types for notion_sync_success metric."""
    CREATE_PAGE = 'create_page'
    UPDATE_PAGE = 'update_page'
    DELETE_PAGE = 'delete_page'
    SYNC_DATABASE = 'sync_database'
    BULK_UPLOAD = 'bulk_upload'


# Job processing statuses
class JobStatuses:
    """Standard job processing statuses."""
    SCRAPED = 'scraped'
    ANALYZED = 'analyzed'
    SAVED = 'saved'
    REJECTED = 'rejected'
    ERROR = 'error'


class ProductionMetrics(JobHunterMetrics):
    """
    Enhanced metrics for production environment.
    Includes system health, performance, and business metrics.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize production metrics."""
        super().__init__(registry)
        
        # System Health Metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'Current CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'Current memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'Current disk usage percentage',
            registry=self.registry
        )
        
        # Request Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
            registry=self.registry
        )
        
        self.http_request_size_bytes = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_response_size_bytes = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database Metrics
        self.database_connections_active = Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.database_query_duration_seconds = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )
        
        self.database_errors_total = Counter(
            'database_errors_total',
            'Total database errors',
            ['error_type'],
            registry=self.registry
        )
        
        # Redis Metrics
        self.redis_operations_total = Counter(
            'redis_operations_total',
            'Total Redis operations',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.redis_operation_duration_seconds = Histogram(
            'redis_operation_duration_seconds',
            'Redis operation duration in seconds',
            ['operation'],
            registry=self.registry
        )
        
        # External API Metrics
        self.external_api_requests_total = Counter(
            'external_api_requests_total',
            'Total external API requests',
            ['service', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.external_api_duration_seconds = Histogram(
            'external_api_duration_seconds',
            'External API request duration in seconds',
            ['service', 'endpoint'],
            registry=self.registry
        )
        
        # Security Metrics
        self.security_events_total = Counter(
            'security_events_total',
            'Total security events',
            ['event_type', 'severity'],
            registry=self.registry
        )
        
        self.rate_limit_hits_total = Counter(
            'rate_limit_hits_total',
            'Total rate limit hits',
            ['endpoint', 'client_type'],
            registry=self.registry
        )
        
        self.authentication_attempts_total = Counter(
            'authentication_attempts_total',
            'Total authentication attempts',
            ['method', 'status'],
            registry=self.registry
        )
        
        # Business Metrics
        self.user_activity_total = Counter(
            'user_activity_total',
            'Total user activity events',
            ['activity_type', 'user_segment'],
            registry=self.registry
        )
        
        self.feature_usage_total = Counter(
            'feature_usage_total',
            'Total feature usage',
            ['feature_name', 'success'],
            registry=self.registry
        )
        
        self.data_export_requests_total = Counter(
            'data_export_requests_total',
            'Total data export requests',
            ['export_format', 'status'],
            registry=self.registry
        )
        
        # Error Tracking
        self.application_errors_total = Counter(
            'application_errors_total',
            'Total application errors',
            ['error_type', 'severity', 'component'],
            registry=self.registry
        )
        
        self.error_recovery_attempts_total = Counter(
            'error_recovery_attempts_total',
            'Total error recovery attempts',
            ['error_type', 'recovery_action', 'success'],
            registry=self.registry
        )
        
        # Performance Metrics
        self.background_task_duration_seconds = Histogram(
            'background_task_duration_seconds',
            'Background task duration in seconds',
            ['task_type'],
            registry=self.registry
        )
        
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.queue_size = Gauge(
            'queue_size',
            'Current queue size',
            ['queue_name'],
            registry=self.registry
        )
    
    def update_system_metrics(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Update system resource metrics."""
        self.system_cpu_usage.set(cpu_percent)
        self.system_memory_usage.set(memory_percent)
        self.system_disk_usage.set(disk_percent)
    
    def record_http_request(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int, 
        duration: float,
        request_size: int = 0,
        response_size: int = 0
    ):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            self.http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            self.http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
    
    def record_database_operation(self, operation: str, duration: float, success: bool = True):
        """Record database operation metrics."""
        self.database_query_duration_seconds.labels(operation=operation).observe(duration)
        
        if not success:
            self.database_errors_total.labels(error_type=operation).inc()
    
    def record_redis_operation(self, operation: str, duration: float, success: bool = True):
        """Record Redis operation metrics."""
        status = 'success' if success else 'error'
        self.redis_operations_total.labels(operation=operation, status=status).inc()
        self.redis_operation_duration_seconds.labels(operation=operation).observe(duration)
    
    def record_external_api_call(
        self, 
        service: str, 
        endpoint: str, 
        status_code: int, 
        duration: float
    ):
        """Record external API call metrics."""
        self.external_api_requests_total.labels(
            service=service,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.external_api_duration_seconds.labels(
            service=service,
            endpoint=endpoint
        ).observe(duration)
    
    def record_security_event(self, event_type: str, severity: str = 'medium'):
        """Record security event."""
        self.security_events_total.labels(
            event_type=event_type,
            severity=severity
        ).inc()
    
    def record_rate_limit_hit(self, endpoint: str, client_type: str = 'anonymous'):
        """Record rate limit hit."""
        self.rate_limit_hits_total.labels(
            endpoint=endpoint,
            client_type=client_type
        ).inc()
    
    def record_authentication_attempt(self, method: str, success: bool):
        """Record authentication attempt."""
        status = 'success' if success else 'failure'
        self.authentication_attempts_total.labels(method=method, status=status).inc()
    
    def record_user_activity(self, activity_type: str, user_segment: str = 'general'):
        """Record user activity."""
        self.user_activity_total.labels(
            activity_type=activity_type,
            user_segment=user_segment
        ).inc()
    
    def record_feature_usage(self, feature_name: str, success: bool = True):
        """Record feature usage."""
        status = 'success' if success else 'failure'
        self.feature_usage_total.labels(feature_name=feature_name, success=status).inc()
    
    def record_data_export(self, export_format: str, success: bool = True):
        """Record data export request."""
        status = 'success' if success else 'failure'
        self.data_export_requests_total.labels(
            export_format=export_format,
            status=status
        ).inc()
    
    def record_application_error(
        self, 
        error_type: str, 
        severity: str = 'medium', 
        component: str = 'unknown'
    ):
        """Record application error."""
        self.application_errors_total.labels(
            error_type=error_type,
            severity=severity,
            component=component
        ).inc()
    
    def record_error_recovery(
        self, 
        error_type: str, 
        recovery_action: str, 
        success: bool
    ):
        """Record error recovery attempt."""
        status = 'success' if success else 'failure'
        self.error_recovery_attempts_total.labels(
            error_type=error_type,
            recovery_action=recovery_action,
            success=status
        ).inc()
    
    def record_background_task(self, task_type: str, duration: float):
        """Record background task execution."""
        self.background_task_duration_seconds.labels(task_type=task_type).observe(duration)
    
    def record_cache_operation(self, operation: str, hit: bool):
        """Record cache operation."""
        result = 'hit' if hit else 'miss'
        self.cache_operations_total.labels(operation=operation, result=result).inc()
    
    def update_queue_size(self, queue_name: str, size: int):
        """Update queue size metric."""
        self.queue_size.labels(queue_name=queue_name).set(size)
    
    def set_active_database_connections(self, count: int):
        """Update active database connections count."""
        self.database_connections_active.set(count)
    
    @contextmanager
    def time_database_operation(self, operation: str):
        """Context manager to time database operations."""
        start_time = time.time()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            self.record_database_operation(operation, duration, success)
    
    @contextmanager
    def time_redis_operation(self, operation: str):
        """Context manager to time Redis operations."""
        start_time = time.time()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            self.record_redis_operation(operation, duration, success)
    
    @contextmanager
    def time_external_api_call(self, service: str, endpoint: str):
        """Context manager to time external API calls."""
        start_time = time.time()
        status_code = 0
        try:
            yield
            status_code = 200  # Default success
        except Exception as e:
            status_code = getattr(e, 'status_code', 500)
            raise
        finally:
            duration = time.time() - start_time
            self.record_external_api_call(service, endpoint, status_code, duration)
    
    @contextmanager
    def time_background_task(self, task_type: str):
        """Context manager to time background tasks."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_background_task(task_type, duration)
    
    def get_health_metrics(self) -> dict:
        """Get key health metrics for monitoring dashboards."""
        from prometheus_client import REGISTRY
        
        # This would normally query the actual metrics
        # For now, returning structure for health dashboard
        return {
            'system': {
                'cpu_usage': 'system_cpu_usage_percent',
                'memory_usage': 'system_memory_usage_percent',
                'disk_usage': 'system_disk_usage_percent'
            },
            'requests': {
                'total_requests': 'http_requests_total',
                'avg_response_time': 'http_request_duration_seconds',
                'error_rate': 'http_requests_total{status_code=~"4..|5.."}'
            },
            'database': {
                'active_connections': 'database_connections_active',
                'query_performance': 'database_query_duration_seconds',
                'error_count': 'database_errors_total'
            },
            'external_apis': {
                'api_calls': 'external_api_requests_total',
                'api_performance': 'external_api_duration_seconds'
            },
            'security': {
                'security_events': 'security_events_total',
                'rate_limit_hits': 'rate_limit_hits_total',
                'auth_failures': 'authentication_attempts_total{status="failure"}'
            }
        }


# Global production metrics instance
production_metrics = ProductionMetrics()

# Export both for backward compatibility
metrics = production_metrics


# Enhanced action types for production
class ActionTypes:
    """Enhanced action types for production monitoring."""
    JOB_SEARCH = 'job_search'
    JOB_VIEW = 'job_view'
    JOB_SAVE = 'job_save'
    JOB_APPLY = 'job_apply'
    JOB_SHARE = 'job_share'
    PROFILE_UPDATE = 'profile_update'
    SETTINGS_CHANGE = 'settings_change'
    EXPORT_DATA = 'export_data'
    FILTER_JOBS = 'filter_jobs'
    SORT_JOBS = 'sort_jobs'
    NOTION_SYNC = 'notion_sync'
    AI_ANALYSIS_REQUEST = 'ai_analysis_request'
    FEEDBACK_SUBMIT = 'feedback_submit'
    ERROR_REPORT = 'error_report'
    FEATURE_FLAG_VIEW = 'feature_flag_view'


class SecurityEventTypes:
    """Security event types for monitoring."""
    SQL_INJECTION_ATTEMPT = 'sql_injection_attempt'
    XSS_ATTEMPT = 'xss_attempt'
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'
    INVALID_AUTH_TOKEN = 'invalid_auth_token'
    SUSPICIOUS_USER_AGENT = 'suspicious_user_agent'
    MULTIPLE_FAILED_LOGINS = 'multiple_failed_logins'
    UNUSUAL_REQUEST_PATTERN = 'unusual_request_pattern'
    DATA_BREACH_ATTEMPT = 'data_breach_attempt'


class FeatureNames:
    """Feature names for usage tracking."""
    JOB_SCRAPING = 'job_scraping'
    AI_MATCHING = 'ai_matching'
    NOTION_INTEGRATION = 'notion_integration'
    LINKEDIN_SCRAPING = 'linkedin_scraping'
    INDEED_SCRAPING = 'indeed_scraping'
    EMAIL_NOTIFICATIONS = 'email_notifications'
    EXPORT_TO_CSV = 'export_to_csv'
    EXPORT_TO_PDF = 'export_to_pdf'
    ADVANCED_FILTERS = 'advanced_filters'
    CUSTOM_KEYWORDS = 'custom_keywords'
    SALARY_TRACKING = 'salary_tracking'
    APPLICATION_STATUS = 'application_status'