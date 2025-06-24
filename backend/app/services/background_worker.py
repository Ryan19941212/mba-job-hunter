"""
Simple Background Worker Service

Basic background task processing without external dependencies.
"""

import asyncio
from typing import Callable, Dict, Any
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BackgroundWorker:
    """Simple background task worker."""
    
    def __init__(self):
        self._tasks = []
        self._running = False
    
    async def add_task(self, func: Callable, *args, **kwargs):
        """Add a task to be executed in the background."""
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'created_at': datetime.utcnow()
        }
        self._tasks.append(task)
        logger.info(f"Added background task: {func.__name__}")
    
    async def process_tasks(self):
        """Process all pending tasks."""
        while self._tasks:
            task = self._tasks.pop(0)
            try:
                if asyncio.iscoroutinefunction(task['func']):
                    await task['func'](*task['args'], **task['kwargs'])
                else:
                    task['func'](*task['args'], **task['kwargs'])
                logger.info(f"Completed task: {task['func'].__name__}")
            except Exception as e:
                logger.error(f"Task failed: {task['func'].__name__}: {e}")
    
    async def start(self):
        """Start processing tasks."""
        self._running = True
        while self._running:
            await self.process_tasks()
            await asyncio.sleep(1)  # Check for tasks every second
    
    def stop(self):
        """Stop the worker."""
        self._running = False


# Global worker instance
background_worker = BackgroundWorker()


# Convenience functions
async def schedule_job_analysis(job_id: int):
    """Schedule a job analysis task."""
    from app.services.analysis_service import AnalysisService
    analysis_service = AnalysisService()
    await background_worker.add_task(analysis_service.analyze_job_basic, job_id)


async def schedule_scraping_task(platform: str, query: str):
    """Schedule a scraping task."""
    logger.info(f"Scheduled scraping task for {platform}: {query}")
    # Implementation would depend on specific scraper