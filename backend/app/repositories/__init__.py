"""
Repository Layer

Data access layer using the repository pattern for clean separation
of database operations from business logic.
"""

from .base_repository import BaseRepository
from .job_repository import JobRepository
from .company_repository import CompanyRepository
from .analysis_repository import AnalysisRepository

__all__ = [
    "BaseRepository",
    "JobRepository", 
    "CompanyRepository",
    "AnalysisRepository"
]