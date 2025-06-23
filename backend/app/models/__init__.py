"""
Database Models Package

Contains SQLAlchemy ORM models for the MBA Job Hunter application.
"""

from app.core.database import Base
from app.models.job import Job

__all__ = [
    "Base",
    "Job",
]