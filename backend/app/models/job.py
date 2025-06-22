"""
Job Database Model

SQLAlchemy model for job postings in the MBA Job Hunter application.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Numeric, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Job(Base):
    """
    Job posting model.
    
    Represents a job posting scraped from various job boards
    or manually added to the system.
    """
    
    __tablename__ = "jobs"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Basic job information
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Company information
    company_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Location and remote work
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Job details
    job_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # full-time, part-time, contract
    experience_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # entry, mid, senior, executive
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Salary information
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD")
    salary_period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # annual, hourly, etc.
    
    # Source information
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # indeed, linkedin, etc.
    source_job_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Posting dates
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Additional metadata
    skills_required: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    benefits: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    additional_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Status and tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    application_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # System fields
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
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationships
    company: Mapped[Optional["Company"]] = relationship(
        "Company", 
        back_populates="jobs",
        lazy="select"
    )
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_job_location_type", "location", "job_type"),
        Index("idx_job_salary_range", "salary_min", "salary_max"),
        Index("idx_job_posted_active", "posted_date", "is_active"),
        Index("idx_job_source_company", "source", "company_id"),
        Index("idx_job_experience_remote", "experience_level", "is_remote"),
    )
    
    def __repr__(self) -> str:
        """String representation of Job."""
        return f"<Job(id={self.id}, title='{self.title}', company_id={self.company_id})>"
    
    @property
    def salary_range_display(self) -> Optional[str]:
        """
        Get formatted salary range display string.
        
        Returns:
            Optional[str]: Formatted salary range or None
        """
        if not self.salary_min and not self.salary_max:
            return None
        
        currency_symbol = "$" if self.salary_currency == "USD" else self.salary_currency
        
        if self.salary_min and self.salary_max:
            return f"{currency_symbol}{self.salary_min:,.0f} - {currency_symbol}{self.salary_max:,.0f}"
        elif self.salary_min:
            return f"{currency_symbol}{self.salary_min:,.0f}+"
        elif self.salary_max:
            return f"Up to {currency_symbol}{self.salary_max:,.0f}"
        
        return None
    
    @property
    def is_recent(self) -> bool:
        """
        Check if job was posted recently (within last 7 days).
        
        Returns:
            bool: True if job is recent
        """
        if not self.posted_date:
            return False
        
        return (datetime.utcnow() - self.posted_date).days <= 7
    
    @property
    def has_salary_info(self) -> bool:
        """
        Check if job has salary information.
        
        Returns:
            bool: True if salary info is available
        """
        return self.salary_min is not None or self.salary_max is not None