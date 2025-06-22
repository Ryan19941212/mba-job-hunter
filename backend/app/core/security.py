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