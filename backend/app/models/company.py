"""
Company Database Model

SQLAlchemy model for companies in the MBA Job Hunter application.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    JSON, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Company(Base):
    """
    Company model.
    
    Represents companies that post job opportunities.
    """
    
    __tablename__ = "companies"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Basic company information
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Company details
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # startup, small, medium, large, enterprise
    type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # public, private, non-profit, etc.
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Location information
    headquarters_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    headquarters_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    headquarters_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    headquarters_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Additional company data
    logo_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    glassdoor_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Ratings and reviews
    glassdoor_rating: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # Out of 5
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Additional metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # e.g., ["tech", "startup", "remote-friendly"]
    benefits: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    culture_keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    additional_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Status and tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_hiring: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    job_count: Mapped[int] = mapped_column(Integer, default=0)  # Current active job count
    
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
    
    # Relationships (will be added after fixing import issues)
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_company_name_industry", "name", "industry"),
        Index("idx_company_location", "headquarters_country", "headquarters_state"),
        Index("idx_company_active_hiring", "is_active", "is_hiring"),
        Index("idx_company_size_type", "size", "type"),
    )
    
    def __repr__(self) -> str:
        """String representation of Company."""
        return f"<Company(id={self.id}, name='{self.name}', industry='{self.industry}')>"
    
    @property
    def display_location(self) -> Optional[str]:
        """
        Get formatted display location.
        
        Returns:
            Optional[str]: Formatted location string
        """
        location_parts = []
        
        if self.headquarters_city:
            location_parts.append(self.headquarters_city)
        
        if self.headquarters_state:
            location_parts.append(self.headquarters_state)
        
        if self.headquarters_country:
            location_parts.append(self.headquarters_country)
        
        return ", ".join(location_parts) if location_parts else None
    
    @property
    def company_age(self) -> Optional[int]:
        """
        Calculate company age in years.
        
        Returns:
            Optional[int]: Company age in years
        """
        if not self.founded_year:
            return None
        
        current_year = datetime.utcnow().year
        return current_year - self.founded_year
    
    @property
    def is_startup(self) -> bool:
        """
        Check if company is a startup (founded within last 10 years or size is startup).
        
        Returns:
            bool: True if company is a startup
        """
        if self.size and self.size.lower() == "startup":
            return True
        
        if self.company_age and self.company_age <= 10:
            return True
        
        return False
    
    @property
    def has_good_rating(self) -> bool:
        """
        Check if company has good rating (>= 4.0).
        
        Returns:
            bool: True if company has good rating
        """
        return self.glassdoor_rating is not None and self.glassdoor_rating >= 4.0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert company to dictionary representation.
        
        Returns:
            Dict[str, Any]: Company as dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "website": self.website,
            "industry": self.industry,
            "size": self.size,
            "type": self.type,
            "founded_year": self.founded_year,
            "headquarters_location": self.headquarters_location,
            "headquarters_country": self.headquarters_country,
            "headquarters_state": self.headquarters_state,
            "headquarters_city": self.headquarters_city,
            "display_location": self.display_location,
            "logo_url": self.logo_url,
            "linkedin_url": self.linkedin_url,
            "glassdoor_url": self.glassdoor_url,
            "glassdoor_rating": self.glassdoor_rating,
            "employee_count": self.employee_count,
            "tags": self.tags,
            "benefits": self.benefits,
            "culture_keywords": self.culture_keywords,
            "additional_info": self.additional_info,
            "is_active": self.is_active,
            "is_hiring": self.is_hiring,
            "job_count": self.job_count,
            "company_age": self.company_age,
            "is_startup": self.is_startup,
            "has_good_rating": self.has_good_rating,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update company fields from dictionary.
        
        Args:
            data: Dictionary with company data
        """
        updatable_fields = {
            "name", "description", "website", "industry", "size", "type",
            "founded_year", "headquarters_location", "headquarters_country",
            "headquarters_state", "headquarters_city", "logo_url",
            "linkedin_url", "glassdoor_url", "glassdoor_rating",
            "employee_count", "tags", "benefits", "culture_keywords",
            "additional_info", "is_active", "is_hiring"
        }
        
        for field, value in data.items():
            if field in updatable_fields and hasattr(self, field):
                setattr(self, field, value)
        
        self.updated_at = datetime.utcnow()
    
    def update_job_count(self) -> None:
        """Update the job count for this company."""
        # This would typically be called after job operations
        # In a real implementation, you'd query the database
        if hasattr(self, 'jobs'):
            self.job_count = len([job for job in self.jobs if job.is_active])
            self.is_hiring = self.job_count > 0