"""
Database Configuration and Session Management

Enhanced database management with production optimizations including
connection pooling, health monitoring, retry logic, and performance tracking.
"""

from typing import AsyncGenerator, Optional, Dict, Any
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool, NullPool
from sqlalchemy import text, event
from sqlalchemy.exc import DisconnectionError, OperationalError
import redis.asyncio as redis
import psutil

from app.core.config import get_settings
from app.utils.logger import get_logger
from app.utils.metrics import production_metrics

# Initialize logger
logger = get_logger(__name__)

# Get settings
settings = get_settings()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class ConnectionPoolMonitor:
    """Monitor database connection pool health and performance."""
    
    def __init__(self):
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'failed_connections': 0,
            'slow_queries': 0,
            'last_health_check': None
        }
        self.slow_query_threshold = 1.0  # seconds
    
    def record_connection_checkout(self):
        """Record connection checkout."""
        self.connection_stats['active_connections'] += 1
        production_metrics.set_active_database_connections(
            self.connection_stats['active_connections']
        )
    
    def record_connection_checkin(self):
        """Record connection checkin."""
        if self.connection_stats['active_connections'] > 0:
            self.connection_stats['active_connections'] -= 1
        production_metrics.set_active_database_connections(
            self.connection_stats['active_connections']
        )
    
    def record_query_execution(self, duration: float, query_type: str = 'unknown'):
        """Record query execution metrics."""
        production_metrics.record_database_operation(query_type, duration)
        
        if duration > self.slow_query_threshold:
            self.connection_stats['slow_queries'] += 1
            logger.warning(
                f"Slow query detected: {duration:.3f}s for {query_type}",
                extra={'duration': duration, 'query_type': query_type}
            )
    
    def record_connection_failure(self):
        """Record connection failure."""
        self.connection_stats['failed_connections'] += 1
        production_metrics.record_database_operation('connection', 0, success=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return self.connection_stats.copy()


class DatabaseManager:
    """Enhanced database connection and session management with production optimizations."""
    
    def __init__(self) -> None:
        """Initialize database manager."""
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._redis_client: Optional[redis.Redis] = None
        self._connection_monitor = ConnectionPoolMonitor()
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = None
        self._health_status = True
        self._retry_config = {
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 30.0,
            'exponential_backoff': True
        }
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._session_factory
    
    @property
    def redis(self) -> Optional[redis.Redis]:
        """Get Redis client."""
        return self._redis_client
    
    async def init_database(self) -> None:
        """Initialize database connections."""
        try:
            # Create async engine
            engine_kwargs = {
                "echo": settings.DEBUG,
            }
            
            # SQLite-specific configuration
            if "sqlite" in str(settings.DATABASE_URL):
                engine_kwargs["poolclass"] = StaticPool
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            else:
                # PostgreSQL-specific configuration
                engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
                engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
            
            self._engine = create_async_engine(
                str(settings.DATABASE_URL),
                **engine_kwargs
            )
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            
            # Initialize Redis (optional for development)
            try:
                self._redis_client = redis.from_url(
                    str(settings.REDIS_URL),
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._test_redis_connection()
            except Exception as e:
                logger.warning(f"Redis connection failed, continuing without cache: {e}")
                self._redis_client = None
            
            # Test database connection
            await self._test_database_connection()
            
            logger.info("Database and Redis connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _test_database_connection(self) -> None:
        """Test database connection."""
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    async def _test_redis_connection(self) -> None:
        """Test Redis connection."""
        try:
            await self._redis_client.ping()
            logger.info("Redis connection test successful")
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            raise
    
    async def create_tables(self) -> None:
        """Create database tables."""
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def close_connections(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database engine disposed")
        
        if self._redis_client:
            await self._redis_client.close()
            logger.info("Redis connection closed")


# Global database manager instance
db_manager = DatabaseManager()


async def init_db() -> None:
    """Initialize database connections and create tables."""
    await db_manager.init_database()
    await db_manager.create_tables()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with db_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with db_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client instance.
    
    Returns:
        redis.Redis: Redis client (None if Redis not available)
    """
    return db_manager.redis


class CacheManager:
    """Redis cache management utilities."""
    
    def __init__(self) -> None:
        """Initialize cache manager."""
        self._redis: Optional[redis.Redis] = None
    
    @property
    def redis(self) -> Optional[redis.Redis]:
        """Get Redis client."""
        if self._redis is None:
            self._redis = db_manager.redis
        return self._redis
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if self.redis is None:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire_seconds: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if self.redis is None:
            return False
        try:
            expire_time = expire_seconds or settings.REDIS_EXPIRE_SECONDS
            return await self.redis.setex(key, expire_time, value)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self.redis is None:
            return False
        try:
            return bool(await self.redis.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if self.redis is None:
            return False
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()