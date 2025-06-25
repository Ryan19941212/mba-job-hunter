"""
Simple Dependency Container

Basic dependency management without external libraries.
"""

from typing import Dict, Any, Optional
from app.core.config import get_settings
from app.core.database import DatabaseManager
from app.core.events import EventManager, event_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleContainer:
    """Simple dependency injection container."""
    
    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize container and dependencies."""
        if self._initialized:
            return
        
        logger.info("Initializing application container...")
        
        # Initialize core services
        settings = get_settings()
        self._instances['settings'] = settings
        
        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.init_database()
        self._instances['db_manager'] = db_manager
        
        # Initialize event manager
        self._instances['event_manager'] = event_manager
        
        self._initialized = True
        logger.info("Container initialized successfully")
    
    async def shutdown(self):
        """Shutdown container and cleanup resources."""
        logger.info("Shutting down container...")
        
        # Cleanup database connections
        if 'db_manager' in self._instances:
            await self._instances['db_manager'].close_connections()
        
        self._instances.clear()
        self._initialized = False
        logger.info("Container shutdown complete")
    
    def get(self, name: str) -> Any:
        """Get dependency by name."""
        return self._instances.get(name)


# Global container instance
container = SimpleContainer()


async def init_container():
    """Initialize the global container."""
    await container.initialize()


async def shutdown_container():
    """Shutdown the global container."""
    await container.shutdown()


def get_container() -> SimpleContainer:
    """Get the global container instance."""
    return container