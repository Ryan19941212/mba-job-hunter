"""
Monitoring Middleware for MBA Job Hunter

Comprehensive monitoring middleware that tracks:
- Request/response times
- Error rates
- API usage statistics
- System resource monitoring
- Custom business metrics
"""

import time
import psutil
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import redis

from app.core.config import get_settings
from app.utils.logger import get_logger
from app.core.security import get_client_ip

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RequestMetrics:
    """Request metrics data structure."""
    
    timestamp: datetime
    method: str
    path: str
    status_code: int
    duration_ms: float
    request_size: int
    response_size: int
    client_ip: str
    user_agent: str
    user_id: Optional[str] = None
    error_type: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System resource metrics."""
    
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    request_rate: float
    error_rate: float
    avg_response_time: float


class MetricsCollector:
    """Collects and stores application metrics."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize metrics collector."""
        self.redis = redis_client
        self.request_metrics: deque = deque(maxlen=10000)  # Keep last 10k requests
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'error_count': 0,
                'last_error': None
            }
        )
        self.hourly_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        
        # Rate tracking windows
        self.request_times: deque = deque(maxlen=1000)
        self.error_times: deque = deque(maxlen=1000)
        
        # System metrics tracking
        self.system_metrics: deque = deque(maxlen=720)  # 12 hours of 1-min intervals
        
        # Start background system monitoring
        if not hasattr(self, '_monitoring_task'):
            self._monitoring_task = None
    
    def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics."""
        self.request_metrics.append(metrics)
        self.request_times.append(metrics.timestamp)
        
        # Update endpoint statistics
        endpoint_key = f"{metrics.method}:{metrics.path}"
        stats = self.endpoint_stats[endpoint_key]
        
        stats['count'] += 1
        stats['total_time'] += metrics.duration_ms
        stats['min_time'] = min(stats['min_time'], metrics.duration_ms)
        stats['max_time'] = max(stats['max_time'], metrics.duration_ms)
        
        # Record errors
        if metrics.status_code >= 400:
            stats['error_count'] += 1
            stats['last_error'] = metrics.timestamp
            self.error_times.append(metrics.timestamp)
            
            error_key = f"{metrics.status_code}:{metrics.error_type or 'unknown'}"
            self.error_counts[error_key] += 1
        
        # Update hourly statistics
        hour_key = metrics.timestamp.strftime('%Y-%m-%d-%H')
        self.hourly_stats[hour_key]['requests'] += 1
        if metrics.status_code >= 400:
            self.hourly_stats[hour_key]['errors'] += 1
        
        # Persist to Redis if available
        if self.redis:
            self._persist_to_redis(metrics)
    
    def record_system_metrics(self) -> None:
        """Record current system metrics."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate rates
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)
            
            recent_requests = [
                t for t in self.request_times 
                if t > minute_ago
            ]
            recent_errors = [
                t for t in self.error_times 
                if t > minute_ago
            ]
            
            request_rate = len(recent_requests)
            error_rate = len(recent_errors) / max(len(recent_requests), 1) * 100
            
            # Calculate average response time
            recent_metrics = [
                m for m in self.request_metrics 
                if m.timestamp > minute_ago
            ]
            avg_response_time = (
                sum(m.duration_ms for m in recent_metrics) / 
                max(len(recent_metrics), 1)
            )
            
            system_metrics = SystemMetrics(
                timestamp=now,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                active_connections=len(self.request_times),
                request_rate=request_rate,
                error_rate=error_rate,
                avg_response_time=avg_response_time
            )
            
            self.system_metrics.append(system_metrics)
            
            # Log system metrics
            logger.info(
                "System metrics recorded",
                extra={
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory.percent,
                    'disk_usage': disk.percent,
                    'request_rate': request_rate,
                    'error_rate': error_rate,
                    'avg_response_time': avg_response_time
                }
            )
            
        except Exception as e:
            logger.error(f"Error recording system metrics: {e}")
    
    def _persist_to_redis(self, metrics: RequestMetrics) -> None:
        """Persist metrics to Redis."""
        try:
            # Store in Redis with TTL
            key = f"metrics:request:{metrics.timestamp.timestamp()}"
            data = {
                'method': metrics.method,
                'path': metrics.path,
                'status_code': metrics.status_code,
                'duration_ms': metrics.duration_ms,
                'client_ip': metrics.client_ip,
                'timestamp': metrics.timestamp.isoformat()
            }
            
            self.redis.hmset(key, data)
            self.redis.expire(key, 86400)  # Keep for 24 hours
            
            # Update counters
            date_key = metrics.timestamp.strftime('%Y-%m-%d')
            hour_key = metrics.timestamp.strftime('%Y-%m-%d-%H')
            
            pipe = self.redis.pipeline()
            pipe.incr(f"metrics:requests:daily:{date_key}")
            pipe.incr(f"metrics:requests:hourly:{hour_key}")
            
            if metrics.status_code >= 400:
                pipe.incr(f"metrics:errors:daily:{date_key}")
                pipe.incr(f"metrics:errors:hourly:{hour_key}")
            
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Error persisting metrics to Redis: {e}")
    
    def get_endpoint_statistics(self) -> Dict[str, Any]:
        """Get endpoint statistics."""
        stats = {}
        
        for endpoint, data in self.endpoint_stats.items():
            if data['count'] > 0:
                stats[endpoint] = {
                    'total_requests': data['count'],
                    'total_errors': data['error_count'],
                    'error_rate': (data['error_count'] / data['count']) * 100,
                    'avg_response_time': data['total_time'] / data['count'],
                    'min_response_time': data['min_time'],
                    'max_response_time': data['max_time'],
                    'last_error': data['last_error'].isoformat() if data['last_error'] else None
                }
        
        return stats
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_breakdown': dict(self.error_counts),
            'top_errors': sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        if not self.request_metrics:
            return {}
        
        durations = [m.duration_ms for m in self.request_metrics]
        durations.sort()
        
        count = len(durations)
        return {
            'total_requests': count,
            'avg_response_time': sum(durations) / count,
            'median_response_time': durations[count // 2],
            'p95_response_time': durations[int(count * 0.95)] if count > 0 else 0,
            'p99_response_time': durations[int(count * 0.99)] if count > 0 else 0,
            'min_response_time': min(durations),
            'max_response_time': max(durations)
        }
    
    def get_current_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        if not self.system_metrics:
            return {}
        
        latest = self.system_metrics[-1]
        return {
            'timestamp': latest.timestamp.isoformat(),
            'cpu_usage': latest.cpu_usage,
            'memory_usage': latest.memory_usage,
            'disk_usage': latest.disk_usage,
            'active_connections': latest.active_connections,
            'request_rate_per_minute': latest.request_rate,
            'error_rate_percent': latest.error_rate,
            'avg_response_time_ms': latest.avg_response_time
        }
    
    async def start_system_monitoring(self) -> None:
        """Start background system monitoring."""
        if self._monitoring_task is not None:
            return
        
        async def monitor_loop():
            while True:
                try:
                    self.record_system_metrics()
                    await asyncio.sleep(60)  # Record every minute
                except Exception as e:
                    logger.error(f"System monitoring error: {e}")
                    await asyncio.sleep(60)
        
        self._monitoring_task = asyncio.create_task(monitor_loop())
    
    def stop_system_monitoring(self) -> None:
        """Stop background system monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring requests and collecting metrics."""
    
    def __init__(
        self,
        app,
        metrics_collector: Optional[MetricsCollector] = None,
        exclude_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.exclude_paths = set(exclude_paths or ['/health', '/metrics'])
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Monitor request and collect metrics."""
        start_time = time.time()
        
        # Skip monitoring for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get request information
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        user_id = getattr(request.state, 'user_id', None)
        
        # Get request size
        request_size = 0
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                request_size = int(content_length)
            except ValueError:
                pass
        
        # Process request
        error_type = None
        try:
            response = await call_next(request)
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Request failed: {e}")
            # Re-raise the exception
            raise
        finally:
            # Calculate metrics
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Get response size
            response_size = 0
            if 'response' in locals():
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        response_size = int(content_length)
                    except ValueError:
                        pass
            
            # Create metrics record
            metrics = RequestMetrics(
                timestamp=datetime.utcnow(),
                method=request.method,
                path=request.url.path,
                status_code=getattr(response, 'status_code', 500) if 'response' in locals() else 500,
                duration_ms=duration_ms,
                request_size=request_size,
                response_size=response_size,
                client_ip=client_ip,
                user_agent=user_agent,
                user_id=user_id,
                error_type=error_type
            )
            
            # Record metrics
            self.metrics_collector.record_request(metrics)
            
            # Add monitoring headers to response
            if 'response' in locals():
                response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
                response.headers["X-Request-ID"] = getattr(request.state, 'request_id', 'unknown')
        
        return response


class HealthCheckMonitor:
    """Monitor health check status and dependencies."""
    
    def __init__(self):
        """Initialize health check monitor."""
        self.health_status = {}
        self.last_check_time = {}
        self.check_interval = 60  # seconds
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        from app.core.database import get_database_session
        
        try:
            start_time = time.time()
            
            # Simple database query
            async with get_database_session() as session:
                await session.execute("SELECT 1")
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            redis_url = getattr(settings, 'REDIS_URL', None)
            if not redis_url:
                return {'status': 'not_configured'}
            
            start_time = time.time()
            redis_client = redis.from_url(redis_url)
            
            # Simple Redis operation
            redis_client.ping()
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def check_external_apis(self) -> Dict[str, Any]:
        """Check external API connectivity."""
        import aiohttp
        
        external_apis = {}
        
        # Check OpenAI API (if configured)
        openai_key = getattr(settings, 'OPENAI_API_KEY', None)
        if openai_key:
            try:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    headers = {'Authorization': f'Bearer {openai_key}'}
                    async with session.get(
                        'https://api.openai.com/v1/models',
                        headers=headers,
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            response_time = (time.time() - start_time) * 1000
                            external_apis['openai'] = {
                                'status': 'healthy',
                                'response_time_ms': response_time
                            }
                        else:
                            external_apis['openai'] = {
                                'status': 'unhealthy',
                                'status_code': response.status
                            }
            except Exception as e:
                external_apis['openai'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        return external_apis
    
    async def get_comprehensive_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        health_checks = {}
        
        # Database health
        health_checks['database'] = await self.check_database_health()
        
        # Redis health
        health_checks['redis'] = await self.check_redis_health()
        
        # External APIs
        health_checks['external_apis'] = await self.check_external_apis()
        
        # System resources
        try:
            health_checks['system'] = {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            health_checks['system'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Overall status
        overall_status = 'healthy'
        for service, status in health_checks.items():
            if isinstance(status, dict):
                if status.get('status') == 'unhealthy':
                    overall_status = 'unhealthy'
                    break
                elif service == 'system':
                    # Check system thresholds
                    if (status.get('cpu_usage', 0) > 90 or 
                        status.get('memory_usage', 0) > 90 or
                        status.get('disk_usage', 0) > 90):
                        overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': health_checks
        }


# Global instances
metrics_collector = MetricsCollector()
health_monitor = HealthCheckMonitor()


def setup_monitoring_middleware(app) -> None:
    """Setup monitoring middleware."""
    app.add_middleware(
        MonitoringMiddleware,
        metrics_collector=metrics_collector,
        exclude_paths=['/health', '/metrics', '/docs', '/redoc', '/openapi.json']
    )


async def start_monitoring() -> None:
    """Start monitoring services."""
    await metrics_collector.start_system_monitoring()


def stop_monitoring() -> None:
    """Stop monitoring services."""
    metrics_collector.stop_system_monitoring()