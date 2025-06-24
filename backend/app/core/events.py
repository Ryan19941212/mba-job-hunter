"""
Simple Event System

Basic event handling for application lifecycle events.
"""

import asyncio
from typing import Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    """Simple event class."""
    name: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class EventManager:
    """Simple event manager for application events."""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
    
    async def emit(self, event_name: str, data: Dict[str, Any] = None) -> None:
        """Emit an event to all registered handlers."""
        if data is None:
            data = {}
            
        event = Event(name=event_name, data=data)
        
        handlers = self._handlers.get(event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event_name}: {e}")
    
    def subscribe(self, event_name: str, handler: Callable) -> None:
        """Subscribe a handler to an event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)
    
    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """Unsubscribe a handler from an event."""
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
            except ValueError:
                pass


# Global event manager instance
event_manager = EventManager()