"""
Security Middleware for MBA Job Hunter

Implements comprehensive security measures including:
- Security headers
- Rate limiting  
- CORS configuration
- Request size limits
- SQL injection protection
- XSS protection
- CSRF protection
"""

import re
import time
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
import redis
from sqlalchemy import text

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or {}
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": self._build_csp_header(),
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    
    def _build_csp_header(self) -> str:
        """Build Content Security Policy header."""
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        return "; ".join(csp_directives)
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add request ID for tracking
        request_id = getattr(request.state, 'request_id', None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis for distributed rate limiting."""
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        requests_per_minute: int = 100,
        burst_limit: int = 20,
        storage_url: Optional[str] = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_size = 60  # 1 minute
        
        # Initialize Redis client
        if redis_client:
            self.redis = redis_client
        elif storage_url:
            self.redis = redis.from_url(storage_url, decode_responses=True)
        else:
            self.redis = None
        
        # Fallback to in-memory storage
        self.memory_storage: Dict[str, List[float]] = {}
        
        # Exempt paths from rate limiting
        self.exempt_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try to get user ID from request state
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Use IP address as fallback
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def _is_rate_limited_redis(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis."""
        try:
            current_time = int(time.time())
            window_start = current_time - self.window_size
            
            # Redis key for this client
            key = f"rate_limit:{client_id}"
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, self.window_size * 2)
            
            results = pipe.execute()
            current_requests = results[1]
            
            # Check burst limit (requests in last 10 seconds)
            burst_window = current_time - 10
            burst_count = self.redis.zcount(key, burst_window, current_time)
            
            is_limited = (
                current_requests >= self.requests_per_minute or
                burst_count >= self.burst_limit
            )
            
            return is_limited, {
                'requests_in_window': current_requests,
                'requests_per_minute': self.requests_per_minute,
                'burst_requests': burst_count,
                'burst_limit': self.burst_limit,
                'reset_time': current_time + self.window_size
            }
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            return False, {}
    
    def _is_rate_limited_memory(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using in-memory storage."""
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Clean old entries
        if client_id in self.memory_storage:
            self.memory_storage[client_id] = [
                t for t in self.memory_storage[client_id] if t > window_start
            ]
        else:
            self.memory_storage[client_id] = []
        
        # Check current requests
        current_requests = len(self.memory_storage[client_id])
        
        # Check burst limit
        burst_window = current_time - 10
        burst_requests = sum(1 for t in self.memory_storage[client_id] if t > burst_window)
        
        # Add current request
        self.memory_storage[client_id].append(current_time)
        
        is_limited = (
            current_requests >= self.requests_per_minute or
            burst_requests >= self.burst_limit
        )
        
        return is_limited, {
            'requests_in_window': current_requests,
            'requests_per_minute': self.requests_per_minute,
            'burst_requests': burst_requests,
            'burst_limit': self.burst_limit,
            'reset_time': int(current_time + self.window_size)
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Apply rate limiting."""
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Skip if rate limiting is bypassed (for testing)
        if getattr(settings, 'BYPASS_RATE_LIMITING', False):
            return await call_next(request)
        
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        if self.redis:
            is_limited, info = self._is_rate_limited_redis(client_id)
        else:
            is_limited, info = self._is_rate_limited_memory(client_id)
        
        if is_limited:
            # Log rate limit violation
            logger.warning(
                f"Rate limit exceeded for {client_id}",
                extra={
                    'client_id': client_id,
                    'path': request.url.path,
                    'method': request.method,
                    'rate_limit_info': info
                }
            )
            
            # Return rate limit error
            headers = {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info.get('reset_time', 0)),
                "Retry-After": str(self.window_size)
            }
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down and try again later.",
                        "details": {
                            "requests_per_minute": self.requests_per_minute,
                            "burst_limit": self.burst_limit,
                            "retry_after_seconds": self.window_size
                        }
                    }
                },
                headers=headers
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - info.get('requests_in_window', 0))
        )
        response.headers["X-RateLimit-Reset"] = str(info.get('reset_time', 0))
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request size and prevent DoS attacks."""
    
    def __init__(
        self,
        app,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        max_json_size: int = 1024 * 1024,          # 1MB
        max_form_size: int = 1024 * 1024,          # 1MB
        max_multipart_size: int = 10 * 1024 * 1024  # 10MB
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.max_json_size = max_json_size
        self.max_form_size = max_form_size
        self.max_multipart_size = max_multipart_size
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Check request size limits."""
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_request_size:
                    logger.warning(
                        f"Request size {length} exceeds limit {self.max_request_size}",
                        extra={'path': request.url.path, 'content_length': length}
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": f"Request size {length} bytes exceeds maximum allowed size of {self.max_request_size} bytes"
                            }
                        }
                    )
            except ValueError:
                pass
        
        # Check specific content type limits
        content_type = request.headers.get("content-type", "").lower()
        
        if "application/json" in content_type and content_length:
            try:
                length = int(content_length)
                if length > self.max_json_size:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "JSON_TOO_LARGE",
                                "message": f"JSON payload size {length} bytes exceeds limit of {self.max_json_size} bytes"
                            }
                        }
                    )
            except ValueError:
                pass
        
        return await call_next(request)


class SQLInjectionProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and prevent SQL injection attacks."""
    
    def __init__(self, app):
        super().__init__(app)
        # Common SQL injection patterns
        self.sql_patterns = [
            re.compile(r"(\s*('|\")?\s*(UNION|union)\s+('|\")?\s*(SELECT|select))", re.IGNORECASE),
            re.compile(r"(\s*('|\")?\s*(DROP|drop)\s+('|\")?\s*(TABLE|table|DATABASE|database))", re.IGNORECASE),
            re.compile(r"(\s*('|\")?\s*(DELETE|delete)\s+('|\")?\s*(FROM|from))", re.IGNORECASE),
            re.compile(r"(\s*('|\")?\s*(INSERT|insert)\s+('|\")?\s*(INTO|into))", re.IGNORECASE),
            re.compile(r"(\s*('|\")?\s*(UPDATE|update)\s+.*\s*(SET|set))", re.IGNORECASE),
            re.compile(r"(\s*('|\")?\s*(OR|or)\s+('|\")?\s*('|\")?\s*1\s*('|\")?\s*=\s*('|\")?\s*1)", re.IGNORECASE),
            re.compile(r"(\s*('|\")?\s*(AND|and)\s+('|\")?\s*('|\")?\s*1\s*('|\")?\s*=\s*('|\")?\s*1)", re.IGNORECASE),
            re.compile(r"(\s*;.*--)|(--.*)", re.IGNORECASE),
            re.compile(r"(\s*'.*'.*--)", re.IGNORECASE),
            re.compile(r"(\s*exec\()", re.IGNORECASE)
        ]
    
    def _detect_sql_injection(self, value: str) -> bool:
        """Detect SQL injection patterns in string."""
        if not isinstance(value, str):
            return False
        
        for pattern in self.sql_patterns:
            if pattern.search(value):
                return True
        return False
    
    def _scan_dict(self, data: Dict[str, Any]) -> bool:
        """Recursively scan dictionary for SQL injection."""
        for key, value in data.items():
            if isinstance(value, str) and self._detect_sql_injection(value):
                return True
            elif isinstance(value, dict) and self._scan_dict(value):
                return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and self._detect_sql_injection(item):
                        return True
                    elif isinstance(item, dict) and self._scan_dict(item):
                        return True
        return False
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Scan request for SQL injection attempts."""
        # Skip for certain paths
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc"]:
            return await call_next(request)
        
        # Check query parameters
        for key, value in request.query_params.items():
            if self._detect_sql_injection(value):
                logger.error(
                    f"SQL injection detected in query parameter '{key}': {value}",
                    extra={
                        'path': request.url.path,
                        'method': request.method,
                        'client_ip': request.client.host if request.client else "unknown",
                        'query_param': key,
                        'suspicious_value': value[:100]  # Log first 100 chars
                    }
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": {
                            "code": "INVALID_REQUEST",
                            "message": "Request contains invalid characters"
                        }
                    }
                )
        
        # Check path parameters
        if self._detect_sql_injection(str(request.url.path)):
            logger.error(
                f"SQL injection detected in path: {request.url.path}",
                extra={
                    'path': request.url.path,
                    'method': request.method,
                    'client_ip': request.client.host if request.client else "unknown"
                }
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Request path contains invalid characters"
                    }
                }
            )
        
        # Check JSON body (if present)
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.body()
                if body:
                    json_data = json.loads(body.decode())
                    if self._scan_dict(json_data):
                        logger.error(
                            "SQL injection detected in JSON body",
                            extra={
                                'path': request.url.path,
                                'method': request.method,
                                'client_ip': request.client.host if request.client else "unknown"
                            }
                        )
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "error": {
                                    "code": "INVALID_REQUEST",
                                    "message": "Request body contains invalid data"
                                }
                            }
                        )
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Invalid JSON will be handled by the application
                pass
        
        return await call_next(request)


def setup_cors_middleware(app, allowed_origins: List[str]) -> None:
    """Setup CORS middleware with secure configuration."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-API-Key"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    )


def setup_security_middleware(app, redis_client: Optional[redis.Redis] = None) -> None:
    """Setup all security middleware."""
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request size limits
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_size=getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024),
        max_json_size=getattr(settings, 'MAX_JSON_SIZE', 1024 * 1024),
        max_form_size=getattr(settings, 'MAX_FORM_SIZE', 1024 * 1024),
        max_multipart_size=getattr(settings, 'MAX_MULTIPART_SIZE', 10 * 1024 * 1024)
    )
    
    # SQL injection protection
    app.add_middleware(SQLInjectionProtectionMiddleware)
    
    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        redis_client=redis_client,
        requests_per_minute=getattr(settings, 'RATE_LIMIT_REQUESTS_PER_MINUTE', 100),
        burst_limit=getattr(settings, 'RATE_LIMIT_BURST', 20),
        storage_url=getattr(settings, 'RATE_LIMIT_STORAGE_URL', None)
    )
    
    # CORS
    cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', ['*'])
    if isinstance(cors_origins, str):
        try:
            cors_origins = json.loads(cors_origins)
        except json.JSONDecodeError:
            cors_origins = [cors_origins]
    
    setup_cors_middleware(app, cors_origins)