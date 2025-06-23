"""
Job Database Model

SQLAlchemy 2.0 model for job postings in the MBA Job Hunter application.
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import (
    Integer, String, Text, DateTime, Boolean, 
    CheckConstraint, Index, UniqueConstraint, ARRAY
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Job(Base):
    """
    Job posting model with AI analysis capabilities.
    
    Represents a job posting scraped from various job boards
    with AI-powered analysis and skill extraction.
    """
    
    __tablename__ = "jobs"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Basic job information
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Salary information
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Job details
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remote_friendly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Dates
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Source information
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    company_logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # AI analysis fields
    ai_fit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Table constraints
    __table_args__ = (
        # Unique constraint on source_url
        UniqueConstraint('source_url', name='uq_job_source_url'),
        
        # Check constraint for ai_fit_score range (0-100)
        CheckConstraint('ai_fit_score >= 0 AND ai_fit_score <= 100', name='ck_job_ai_fit_score_range'),
        
        # Check constraint for valid employment types
        CheckConstraint(
            "employment_type IN ('Full-time', 'Part-time', 'Contract') OR employment_type IS NULL", 
            name='ck_job_employment_type_valid'
        ),
        
        # Check constraint for valid source platforms
        CheckConstraint(
            "source_platform IN ('linkedin', 'indeed', 'levelfyi')", 
            name='ck_job_source_platform_valid'
        ),
        
        # Indexes for performance
        Index('idx_job_title', 'title'),
        Index('idx_job_company_name', 'company_name'),
        Index('idx_job_location', 'location'),
        Index('idx_job_salary_range', 'salary_min', 'salary_max'),
        Index('idx_job_employment_type', 'employment_type'),
        Index('idx_job_remote_friendly', 'remote_friendly'),
        Index('idx_job_posted_date', 'posted_date'),
        Index('idx_job_source_platform', 'source_platform'),
        Index('idx_job_ai_fit_score', 'ai_fit_score'),
        Index('idx_job_is_active', 'is_active'),
        Index('idx_job_created_at', 'created_at'),
        
        # Composite indexes for common queries
        Index('idx_job_active_posted', 'is_active', 'posted_date'),
        Index('idx_job_platform_active', 'source_platform', 'is_active'),
        Index('idx_job_company_active', 'company_name', 'is_active'),
        Index('idx_job_location_remote', 'location', 'remote_friendly'),
    )
    
    def __repr__(self) -> str:
        """String representation of Job."""
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company_name}')>"
    
    @property
    def salary_range_display(self) -> Optional[str]:
        """
        Get formatted salary range display string.
        
        Returns:
            Optional[str]: Formatted salary range or None
        """
        if not self.salary_min and not self.salary_max:
            return None
        
        currency_symbol = "$" if self.currency == "USD" else self.currency
        
        if self.salary_min and self.salary_max:
            return f"{currency_symbol}{self.salary_min:,} - {currency_symbol}{self.salary_max:,}"
        elif self.salary_min:
            return f"{currency_symbol}{self.salary_min:,}+"
        elif self.salary_max:
            return f"Up to {currency_symbol}{self.salary_max:,}"
        
        return None
    
    @property
    def is_recent(self) -> bool:
        """
        Check if job was posted recently (within last 30 days).
        
        Returns:
            bool: True if job is recent
        """
        if not self.posted_date:
            return False
        
        return (datetime.utcnow() - self.posted_date).days <= 30
    
    @property
    def has_salary_info(self) -> bool:
        """
        Check if job has salary information.
        
        Returns:
            bool: True if salary info is available
        """
        return self.salary_min is not None or self.salary_max is not None
    
    @property
    def is_expired(self) -> bool:
        """
        Check if job posting has expired.
        
        Returns:
            bool: True if job has expired
        """
        if not self.expires_date:
            return False
        
        return datetime.utcnow() > self.expires_date