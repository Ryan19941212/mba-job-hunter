"""
Security and Authentication

Handles JWT token creation/validation, password hashing,
and security-related utilities for the MBA Job Hunter application.
"""

from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import secrets
import hashlib
import hmac

from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get settings
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


class SecurityManager:
    """Security and authentication manager."""
    
    def __init__(self) -> None:
        """Initialize security manager."""
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Payload data to encode
            expires_delta: Token expiration time
            
        Returns:
            str: Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode, 
                self.secret_key, 
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Dict[str, Any]: Decoded token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Check if token has expired
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return payload
            
        except JWTError as e:
            logger.error(f"JWT verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            bool: True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def generate_api_key(self, length: int = 32) -> str:
        """
        Generate secure API key.
        
        Args:
            length: Length of the API key
            
        Returns:
            str: Generated API key
        """
        return secrets.token_urlsafe(length)
    
    def generate_webhook_signature(self, payload: str, secret: str) -> str:
        """
        Generate webhook signature for payload verification.
        
        Args:
            payload: Webhook payload
            secret: Webhook secret
            
        Returns:
            str: HMAC signature
        """
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        secret: str
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Webhook payload
            signature: Provided signature
            secret: Webhook secret
            
        Returns:
            bool: True if signature is valid
        """
        expected_signature = self.generate_webhook_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)


# Global security manager instance
security_manager = SecurityManager()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict[str, Any]: Current user information
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = security_manager.verify_token(token)
    
    # Extract user information from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "scopes": payload.get("scopes", []),
        "exp": payload.get("exp"),
        "iat": payload.get("iat")
    }


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[Dict[str, Any]]:
    """
    Dependency to get current user (optional).
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Optional[Dict[str, Any]]: Current user information or None
    """
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_scopes(*required_scopes: str):
    """
    Decorator to require specific scopes for endpoint access.
    
    Args:
        *required_scopes: Required scopes
        
    Returns:
        Callable: Dependency function
    """
    async def check_scopes(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_scopes = set(current_user.get("scopes", []))
        required_scopes_set = set(required_scopes)
        
        if not required_scopes_set.issubset(user_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return check_scopes


class RateLimiter:
    """Simple rate limiting implementation."""
    
    def __init__(self) -> None:
        """Initialize rate limiter."""
        self._requests: Dict[str, list] = {}
        self.max_requests = settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = 60
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for identifier.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            
        Returns:
            bool: True if request is allowed
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        # Remove old requests outside the window
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier] 
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self._requests[identifier]) >= self.max_requests:
            return False
        
        # Add current request
        self._requests[identifier].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


class EncryptionManager:
    """Manager for encrypting/decrypting sensitive data."""
    
    def __init__(self, key: Optional[str] = None):
        """Initialize encryption manager."""
        from cryptography.fernet import Fernet
        import base64
        
        if key:
            # Use provided key
            self.key = key.encode()
        else:
            # Generate key from secret
            key_material = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            self.key = base64.urlsafe_b64encode(key_material)
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            str: Encrypted data (base64 encoded)
        """
        try:
            encrypted_data = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Encrypted data (base64 encoded)
            
        Returns:
            str: Decrypted data
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Dict[str, Any]: Dictionary with encrypted fields
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
            
        Returns:
            Dict[str, Any]: Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {e}")
                    # Keep original value if decryption fails
                    pass
        
        return decrypted_data


class APIKeyManager:
    """Manager for API key validation and management."""
    
    def __init__(self):
        """Initialize API key manager."""
        self.valid_api_keys = set()
        self.api_key_scopes: Dict[str, List[str]] = {}
        self.api_key_rate_limits: Dict[str, Dict[str, Any]] = {}
    
    def add_api_key(
        self, 
        api_key: str, 
        scopes: List[str] = None,
        rate_limit: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add valid API key.
        
        Args:
            api_key: API key to add
            scopes: List of scopes for this API key
            rate_limit: Rate limiting configuration
        """
        self.valid_api_keys.add(api_key)
        self.api_key_scopes[api_key] = scopes or []
        if rate_limit:
            self.api_key_rate_limits[api_key] = rate_limit
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            bool: True if valid
        """
        return api_key in self.valid_api_keys
    
    def get_api_key_scopes(self, api_key: str) -> List[str]:
        """
        Get scopes for API key.
        
        Args:
            api_key: API key
            
        Returns:
            List[str]: List of scopes
        """
        return self.api_key_scopes.get(api_key, [])
    
    def get_api_key_rate_limit(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Get rate limit configuration for API key.
        
        Args:
            api_key: API key
            
        Returns:
            Optional[Dict[str, Any]]: Rate limit configuration
        """
        return self.api_key_rate_limits.get(api_key)


class DataSanitizer:
    """Sanitizer for input data to prevent XSS and other attacks."""
    
    def __init__(self):
        """Initialize sanitizer."""
        import html
        self.html = html
        
        # Dangerous HTML tags and attributes
        self.dangerous_tags = {
            'script', 'style', 'iframe', 'object', 'embed', 
            'form', 'input', 'textarea', 'select', 'button',
            'link', 'meta', 'base'
        }
        
        self.dangerous_attributes = {
            'onclick', 'onload', 'onerror', 'onmouseover',
            'onsubmit', 'onfocus', 'onblur', 'onchange',
            'javascript:', 'vbscript:', 'data:'
        }
    
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize string input.
        
        Args:
            value: String to sanitize
            
        Returns:
            str: Sanitized string
        """
        if not isinstance(value, str):
            return value
        
        # HTML escape
        sanitized = self.html.escape(value)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Remove control characters except tab, newline, carriage return
        sanitized = ''.join(
            char for char in sanitized 
            if ord(char) >= 32 or char in '\t\n\r'
        )
        
        return sanitized
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Dict[str, Any]: Sanitized dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            sanitized_key = self.sanitize_string(key)
            
            # Sanitize value
            if isinstance(value, str):
                sanitized[sanitized_key] = self.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[sanitized_key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[sanitized_key] = [
                    self.sanitize_string(item) if isinstance(item, str)
                    else self.sanitize_dict(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[sanitized_key] = value
        
        return sanitized
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email to validate
            
        Returns:
            bool: True if valid email format
        """
        import re
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(email_pattern.match(email))
    
    def validate_url(self, url: str, allowed_schemes: List[str] = None) -> bool:
        """
        Validate URL format and scheme.
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes
            
        Returns:
            bool: True if valid URL
        """
        from urllib.parse import urlparse
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in allowed_schemes and
                parsed.netloc and
                len(url) <= 2048  # Reasonable URL length limit
            )
        except Exception:
            return False


class SecurityAuditLogger:
    """Logger for security events and audit trails."""
    
    def __init__(self):
        """Initialize security audit logger."""
        self.security_logger = get_logger("security_audit")
    
    def log_authentication_attempt(
        self,
        user_identifier: str,
        success: bool,
        ip_address: str,
        user_agent: str = None,
        additional_info: Dict[str, Any] = None
    ) -> None:
        """
        Log authentication attempt.
        
        Args:
            user_identifier: User identifier (email, username, etc.)
            success: Whether authentication was successful
            ip_address: Client IP address
            user_agent: Client user agent
            additional_info: Additional information
        """
        log_data = {
            'event_type': 'authentication_attempt',
            'user_identifier': user_identifier,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.utcnow().isoformat(),
            **(additional_info or {})
        }
        
        if success:
            self.security_logger.info("Authentication successful", extra=log_data)
        else:
            self.security_logger.warning("Authentication failed", extra=log_data)
    
    def log_api_key_usage(
        self,
        api_key_hash: str,
        endpoint: str,
        ip_address: str,
        success: bool,
        additional_info: Dict[str, Any] = None
    ) -> None:
        """
        Log API key usage.
        
        Args:
            api_key_hash: Hash of the API key (not the key itself)
            endpoint: API endpoint accessed
            ip_address: Client IP address
            success: Whether request was successful
            additional_info: Additional information
        """
        log_data = {
            'event_type': 'api_key_usage',
            'api_key_hash': api_key_hash,
            'endpoint': endpoint,
            'ip_address': ip_address,
            'success': success,
            'timestamp': datetime.utcnow().isoformat(),
            **(additional_info or {})
        }
        
        self.security_logger.info("API key usage", extra=log_data)
    
    def log_rate_limit_violation(
        self,
        identifier: str,
        endpoint: str,
        ip_address: str,
        limit_type: str,
        additional_info: Dict[str, Any] = None
    ) -> None:
        """
        Log rate limit violation.
        
        Args:
            identifier: Client identifier
            endpoint: API endpoint
            ip_address: Client IP address
            limit_type: Type of rate limit violated
            additional_info: Additional information
        """
        log_data = {
            'event_type': 'rate_limit_violation',
            'identifier': identifier,
            'endpoint': endpoint,
            'ip_address': ip_address,
            'limit_type': limit_type,
            'timestamp': datetime.utcnow().isoformat(),
            **(additional_info or {})
        }
        
        self.security_logger.warning("Rate limit violation", extra=log_data)
    
    def log_security_threat(
        self,
        threat_type: str,
        severity: str,
        ip_address: str,
        details: Dict[str, Any],
        user_identifier: str = None
    ) -> None:
        """
        Log security threat.
        
        Args:
            threat_type: Type of security threat
            severity: Severity level (low, medium, high, critical)
            ip_address: Client IP address
            details: Threat details
            user_identifier: User identifier if applicable
        """
        log_data = {
            'event_type': 'security_threat',
            'threat_type': threat_type,
            'severity': severity,
            'ip_address': ip_address,
            'user_identifier': user_identifier,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if severity in ['high', 'critical']:
            self.security_logger.error("Security threat detected", extra=log_data)
        else:
            self.security_logger.warning("Security threat detected", extra=log_data)


# Global instances
encryption_manager = EncryptionManager()
api_key_manager = APIKeyManager()
data_sanitizer = DataSanitizer()
security_audit_logger = SecurityAuditLogger()


def get_client_ip(request) -> str:
    """
    Extract client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers (common in production behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (client IP)
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


def create_request_fingerprint(request) -> str:
    """
    Create unique fingerprint for request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Request fingerprint
    """
    components = [
        get_client_ip(request),
        request.headers.get("User-Agent", ""),
        request.headers.get("Accept-Language", ""),
        request.headers.get("Accept-Encoding", "")
    ]
    
    fingerprint_string = "|".join(components)
    return hashlib.md5(fingerprint_string.encode()).hexdigest()


async def validate_request_integrity(request) -> bool:
    """
    Validate request integrity and detect anomalies.
    
    Args:
        request: FastAPI request object
        
    Returns:
        bool: True if request appears legitimate
    """
    # Check user agent
    user_agent = request.headers.get("User-Agent", "")
    if not user_agent or len(user_agent) > 1000:
        return False
    
    # Check for suspicious headers
    suspicious_headers = [
        "X-Forwarded-Host", "X-Original-URL", "X-Rewrite-URL"
    ]
    
    for header in suspicious_headers:
        if header in request.headers:
            logger.warning(f"Suspicious header detected: {header}")
    
    # Validate content type for POST/PUT requests
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("Content-Type", "")
        if content_type and not any(
            allowed_type in content_type.lower() 
            for allowed_type in [
                "application/json", 
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain"
            ]
        ):
            logger.warning(f"Unexpected content type: {content_type}")
    
    return True