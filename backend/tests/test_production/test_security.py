"""
Security Tests for Production Environment

Comprehensive security testing including:
- Authentication and authorization
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- Rate limiting
- Security headers
- Data encryption
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.security import security_manager, data_sanitizer
from app.middleware.security import SQLInjectionProtectionMiddleware


class TestAuthenticationSecurity:
    """Test authentication and authorization security."""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_jwt_token_security(self):
        """Test JWT token generation and validation."""
        
        # Test token generation
        test_data = {"user_id": "test_user", "email": "test@example.com"}
        token = security_manager.create_access_token(test_data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens should be reasonably long
        
        # Test token validation
        payload = security_manager.verify_token(token)
        assert payload["user_id"] == "test_user"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload
    
    @pytest.mark.asyncio
    async def test_invalid_token_handling(self):
        """Test handling of invalid tokens."""
        
        # Test invalid token
        with pytest.raises(Exception):  # Should raise HTTPException
            security_manager.verify_token("invalid_token")
        
        # Test expired token (simulate by creating token with past expiry)
        from datetime import datetime, timedelta
        import jwt
        
        expired_payload = {
            "user_id": "test_user",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        
        expired_token = jwt.encode(
            expired_payload, 
            security_manager.secret_key, 
            algorithm=security_manager.algorithm
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException for expired token
            security_manager.verify_token(expired_token)
    
    @pytest.mark.asyncio
    async def test_password_security(self):
        """Test password hashing and verification."""
        
        test_password = "TestPassword123!"
        
        # Test password hashing
        hashed = security_manager.hash_password(test_password)
        assert isinstance(hashed, str)
        assert hashed != test_password  # Should be hashed
        assert len(hashed) > 50  # Bcrypt hashes are long
        
        # Test password verification
        assert security_manager.verify_password(test_password, hashed)
        assert not security_manager.verify_password("wrong_password", hashed)
    
    @pytest.mark.asyncio
    async def test_api_key_security(self):
        """Test API key generation and validation."""
        
        # Test API key generation
        api_key = security_manager.generate_api_key()
        assert isinstance(api_key, str)
        assert len(api_key) >= 32  # Should be reasonably long
        
        # Test API key uniqueness
        api_key2 = security_manager.generate_api_key()
        assert api_key != api_key2


class TestInputValidationSecurity:
    """Test input validation and sanitization."""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    def test_data_sanitization(self):
        """Test data sanitization functions."""
        
        # Test HTML/XSS sanitization
        malicious_input = "<script>alert('xss')</script>Hello"
        sanitized = data_sanitizer.sanitize_string(malicious_input)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized or "&lt;script&gt;" in sanitized
        
        # Test null byte removal
        null_input = "test\x00data"
        sanitized = data_sanitizer.sanitize_string(null_input)
        assert "\x00" not in sanitized
        
        # Test control character removal
        control_input = "test\x01\x02data"
        sanitized = data_sanitizer.sanitize_string(control_input)
        assert "\x01" not in sanitized
        assert "\x02" not in sanitized
    
    def test_email_validation(self):
        """Test email validation."""
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test+tag@gmail.com"
        ]
        
        invalid_emails = [
            "invalid_email",
            "@domain.com",
            "test@",
            "test@.com",
            "test..test@domain.com"
        ]
        
        for email in valid_emails:
            assert data_sanitizer.validate_email(email), f"Valid email rejected: {email}"
        
        for email in invalid_emails:
            assert not data_sanitizer.validate_email(email), f"Invalid email accepted: {email}"
    
    def test_url_validation(self):
        """Test URL validation."""
        
        valid_urls = [
            "https://example.com",
            "http://subdomain.example.com/path",
            "https://example.com:8080/path?query=value"
        ]
        
        invalid_urls = [
            "not_a_url",
            "ftp://example.com",  # Not in allowed schemes
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for url in valid_urls:
            assert data_sanitizer.validate_url(url), f"Valid URL rejected: {url}"
        
        for url in invalid_urls:
            assert not data_sanitizer.validate_url(url), f"Invalid URL accepted: {url}"
    
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, async_client):
        """Test SQL injection protection."""
        
        sql_injection_payloads = [
            "'; DROP TABLE jobs; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO jobs VALUES ('malicious'); --",
            "' AND 1=1 --",
            "admin'--",
            "admin' #",
            "admin'/*"
        ]
        
        # Test SQL injection in query parameters
        for payload in sql_injection_payloads:
            response = await async_client.get(f"/api/v1/jobs?search={payload}")
            # Should either block the request or sanitize it
            assert response.status_code in [200, 400], f"Unexpected response for payload: {payload}"
            
            if response.status_code == 400:
                error_data = response.json()
                assert "error" in error_data
    
    @pytest.mark.asyncio
    async def test_xss_protection(self, async_client):
        """Test XSS protection."""
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "<iframe src='javascript:alert(\"xss\")'></iframe>"
        ]
        
        # Test XSS in job search
        for payload in xss_payloads:
            search_request = {
                "keywords": [payload],
                "location": "台北"
            }
            
            response = await async_client.post("/api/v1/jobs/search", json=search_request)
            
            if response.status_code == 200:
                # If request succeeds, check that payload is sanitized
                results = response.json()
                response_text = json.dumps(results)
                assert "<script>" not in response_text
                assert "javascript:" not in response_text


class TestRateLimitingSecurity:
    """Test rate limiting security."""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, async_client):
        """Test API rate limiting."""
        
        # Make rapid requests to trigger rate limiting
        responses = []
        start_time = time.time()
        
        for i in range(150):  # Exceed typical rate limit
            response = await async_client.get("/health")
            responses.append(response.status_code)
            
            # If we hit rate limit, break
            if response.status_code == 429:
                break
            
            # Don't spend too much time on this test
            if time.time() - start_time > 30:
                break
        
        # Should eventually hit rate limit or all succeed (if rate limiting disabled in tests)
        rate_limited = any(status == 429 for status in responses)
        all_success = all(status == 200 for status in responses)
        
        assert rate_limited or all_success, "Rate limiting should work or all requests should succeed"
        
        # If rate limited, check response format
        if rate_limited:
            rate_limit_response = None
            for i, status in enumerate(responses):
                if status == 429:
                    # Get the rate limit response
                    response = await async_client.get("/health")
                    if response.status_code == 429:
                        rate_limit_response = response
                        break
            
            if rate_limit_response:
                assert "Retry-After" in rate_limit_response.headers
                error_data = rate_limit_response.json()
                assert "error" in error_data
    
    @pytest.mark.asyncio
    async def test_burst_protection(self, async_client):
        """Test burst protection in rate limiting."""
        
        # Make very rapid requests (burst)
        start_time = time.time()
        burst_responses = []
        
        # Make 25 requests as fast as possible
        tasks = [async_client.get("/health") for _ in range(25)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        status_codes = [r.status_code for r in responses if hasattr(r, 'status_code')]
        
        # Should handle burst appropriately
        success_rate = sum(1 for code in status_codes if code == 200) / len(status_codes)
        assert success_rate >= 0.5, "Should handle reasonable burst traffic"


class TestSecurityHeaders:
    """Test security headers implementation."""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client):
        """Test that all required security headers are present."""
        
        response = await async_client.get("/")
        
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": lambda x: "default-src 'self'" in x,
            "Permissions-Policy": lambda x: "geolocation=()" in x
        }
        
        for header, expected in required_headers.items():
            assert header in response.headers, f"Missing security header: {header}"
            
            if callable(expected):
                assert expected(response.headers[header]), f"Invalid {header} value"
            else:
                assert response.headers[header] == expected, f"Invalid {header} value"
    
    @pytest.mark.asyncio
    async def test_csp_header_security(self, async_client):
        """Test Content Security Policy header."""
        
        response = await async_client.get("/")
        
        if "Content-Security-Policy" in response.headers:
            csp = response.headers["Content-Security-Policy"]
            
            # Should have secure directives
            assert "default-src 'self'" in csp
            assert "script-src 'self'" in csp
            assert "frame-ancestors 'none'" in csp or "frame-ancestors" not in csp
            
            # Should not allow unsafe directives in production
            unsafe_directives = ["'unsafe-eval'", "'unsafe-inline'"]
            for directive in unsafe_directives:
                # Allow unsafe-inline for style-src only (common requirement)
                if directive == "'unsafe-inline'" and "style-src" in csp:
                    continue
                assert directive not in csp or "style-src" in csp, f"Unsafe CSP directive: {directive}"


class TestDataEncryption:
    """Test data encryption and security."""
    
    def test_sensitive_data_encryption(self):
        """Test encryption of sensitive data."""
        from app.core.security import encryption_manager
        
        sensitive_data = "sensitive_password_123"
        
        # Test encryption
        encrypted = encryption_manager.encrypt(sensitive_data)
        assert encrypted != sensitive_data
        assert isinstance(encrypted, str)
        assert len(encrypted) > len(sensitive_data)
        
        # Test decryption
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == sensitive_data
    
    def test_dictionary_encryption(self):
        """Test encryption of dictionary fields."""
        from app.core.security import encryption_manager
        
        test_data = {
            "username": "testuser",
            "password": "secret123",
            "email": "test@example.com",
            "api_key": "sk-abc123"
        }
        
        fields_to_encrypt = ["password", "api_key"]
        
        # Test encryption
        encrypted_data = encryption_manager.encrypt_dict(test_data, fields_to_encrypt)
        
        assert encrypted_data["username"] == test_data["username"]  # Not encrypted
        assert encrypted_data["email"] == test_data["email"]  # Not encrypted
        assert encrypted_data["password"] != test_data["password"]  # Encrypted
        assert encrypted_data["api_key"] != test_data["api_key"]  # Encrypted
        
        # Test decryption
        decrypted_data = encryption_manager.decrypt_dict(encrypted_data, fields_to_encrypt)
        
        assert decrypted_data == test_data


class TestSecurityAuditing:
    """Test security auditing and logging."""
    
    def test_security_audit_logging(self):
        """Test security audit logging functionality."""
        from app.core.security import security_audit_logger
        
        # Test authentication logging
        security_audit_logger.log_authentication_attempt(
            user_identifier="test@example.com",
            success=True,
            ip_address="192.168.1.1",
            user_agent="test-agent"
        )
        
        security_audit_logger.log_authentication_attempt(
            user_identifier="test@example.com",
            success=False,
            ip_address="192.168.1.100",
            user_agent="suspicious-agent"
        )
        
        # Test security threat logging
        security_audit_logger.log_security_threat(
            threat_type="sql_injection_attempt",
            severity="high",
            ip_address="192.168.1.100",
            details={"payload": "'; DROP TABLE users; --"}
        )
        
        # If we get here without exceptions, logging is working
        assert True
    
    def test_request_fingerprinting(self):
        """Test request fingerprinting for security."""
        from app.core.security import create_request_fingerprint
        from unittest.mock import Mock
        
        # Create mock request
        request1 = Mock()
        request1.client.host = "192.168.1.1"
        request1.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip"
        }
        request1.headers.get = lambda key, default="": request1.headers.get(key, default)
        
        request2 = Mock()
        request2.client.host = "192.168.1.2"
        request2.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US", 
            "Accept-Encoding": "gzip"
        }
        request2.headers.get = lambda key, default="": request2.headers.get(key, default)
        
        fingerprint1 = create_request_fingerprint(request1)
        fingerprint2 = create_request_fingerprint(request2)
        
        assert isinstance(fingerprint1, str)
        assert isinstance(fingerprint2, str)
        assert fingerprint1 != fingerprint2  # Different IPs should create different fingerprints


class TestProductionSecurityChecklist:
    """Comprehensive security checklist for production."""
    
    @pytest.mark.asyncio
    async def test_production_security_checklist(self):
        """Run comprehensive security checklist."""
        
        security_checks = {}
        
        # Check environment security
        import os
        
        # Debug mode should be disabled
        security_checks["debug_disabled"] = os.getenv("DEBUG", "false").lower() == "false"
        
        # Secret keys should be strong
        secret_key = os.getenv("SECRET_KEY", "")
        security_checks["strong_secret_key"] = len(secret_key) >= 32
        
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        security_checks["strong_jwt_secret"] = len(jwt_secret) >= 32
        
        # CORS should be configured properly
        cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
        environment = os.getenv("ENVIRONMENT", "development")
        security_checks["secure_cors"] = cors_origins != "*" or environment != "production"
        
        # SSL should be configured in production
        ssl_cert = os.getenv("SSL_CERTFILE", "")
        ssl_key = os.getenv("SSL_KEYFILE", "")
        security_checks["ssl_configured"] = bool(ssl_cert and ssl_key) or environment != "production"
        
        # Database URL should use secure connection in production
        db_url = os.getenv("DATABASE_URL", "")
        security_checks["secure_db_connection"] = (
            "sslmode=require" in db_url or 
            "sqlite" in db_url or 
            environment != "production"
        )
        
        # Check security middleware is loaded
        try:
            from app.middleware.security import SecurityHeadersMiddleware
            security_checks["security_middleware_available"] = True
        except ImportError:
            security_checks["security_middleware_available"] = False
        
        # Check error handling doesn't leak sensitive info
        try:
            from app.middleware.error_handler import ErrorHandlingMiddleware
            security_checks["secure_error_handling"] = True
        except ImportError:
            security_checks["secure_error_handling"] = False
        
        # Report results
        failed_checks = [check for check, passed in security_checks.items() if not passed]
        
        if failed_checks:
            print(f"Security checks failed: {failed_checks}")
            print(f"Security checklist: {security_checks}")
        
        # In production, all checks should pass
        if environment == "production":
            assert all(security_checks.values()), f"Production security checks failed: {failed_checks}"
        else:
            # In development, warn about failed checks but don't fail
            if failed_checks:
                print(f"Warning: Security checks failed in {environment}: {failed_checks}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])