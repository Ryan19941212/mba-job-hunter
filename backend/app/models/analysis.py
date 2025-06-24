"""
Analysis Database Model

SQLAlchemy model for AI-powered job analyses in the MBA Job Hunter application.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Float, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Analysis(Base):
    """
    Job analysis model.
    
    Stores AI-powered analysis results for jobs, including
    match scores, insights, and recommendations.
    """
    
    __tablename__ = "analyses"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Related entities
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Analysis metadata
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # job_match, market_analysis, trend_analysis
    analysis_version: Mapped[str] = mapped_column(String(20), default="1.0")
    ai_model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # gpt-4, claude-3, etc.
    
    # Analysis results
    results: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Scoring and confidence
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)  # 0.0 to 1.0
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)  # 0.0 to 1.0
    
    # Detailed scores (if applicable)
    skill_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    culture_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Analysis insights
    key_insights: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    red_flags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Processing status
    status: Mapped[str] = mapped_column(String(20), default="completed", index=True)  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
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
        Index("idx_analysis_job_user", "job_id", "user_id"),
        Index("idx_analysis_type_status", "analysis_type", "status"),
        Index("idx_analysis_match_confidence", "match_score", "confidence_score"),
        Index("idx_analysis_created", "created_at"),
        Index("idx_analysis_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        """String representation of Analysis."""
        return f"<Analysis(id={self.id}, job_id={self.job_id}, type='{self.analysis_type}', score={self.match_score})>"
    
    @property
    def is_high_match(self) -> bool:
        """
        Check if this is a high match (score >= 0.8).
        
        Returns:
            bool: True if high match
        """
        return self.match_score is not None and self.match_score >= 0.8
    
    @property
    def is_good_match(self) -> bool:
        """
        Check if this is a good match (score >= 0.6).
        
        Returns:
            bool: True if good match
        """
        return self.match_score is not None and self.match_score >= 0.6
    
    @property
    def match_level(self) -> str:
        """
        Get match level description.
        
        Returns:
            str: Match level (excellent, good, fair, poor)
        """
        if not self.match_score:
            return "unknown"
        
        if self.match_score >= 0.9:
            return "excellent"
        elif self.match_score >= 0.7:
            return "good"
        elif self.match_score >= 0.5:
            return "fair"
        else:
            return "poor"
    
    @property
    def confidence_level(self) -> str:
        """
        Get confidence level description.
        
        Returns:
            str: Confidence level (high, medium, low)
        """
        if self.confidence_score >= 0.8:
            return "high"
        elif self.confidence_score >= 0.6:
            return "medium"
        else:
            return "low"
    
    @property
    def is_recent(self) -> bool:
        """
        Check if analysis is recent (within last 24 hours).
        
        Returns:
            bool: True if analysis is recent
        """
        return (datetime.utcnow() - self.created_at).days == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert analysis to dictionary representation.
        
        Returns:
            Dict[str, Any]: Analysis as dictionary
        """
        return {
            "id": self.id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "analysis_type": self.analysis_type,
            "analysis_version": self.analysis_version,
            "ai_model_used": self.ai_model_used,
            "results": self.results,
            "confidence_score": self.confidence_score,
            "match_score": self.match_score,
            "skill_match_score": self.skill_match_score,
            "experience_match_score": self.experience_match_score,
            "location_match_score": self.location_match_score,
            "salary_match_score": self.salary_match_score,
            "culture_match_score": self.culture_match_score,
            "key_insights": self.key_insights,
            "recommendations": self.recommendations,
            "red_flags": self.red_flags,
            "status": self.status,
            "error_message": self.error_message,
            "processing_time_seconds": self.processing_time_seconds,
            "match_level": self.match_level,
            "confidence_level": self.confidence_level,
            "is_high_match": self.is_high_match,
            "is_good_match": self.is_good_match,
            "is_recent": self.is_recent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def update_scores(
        self,
        match_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
        skill_match: Optional[float] = None,
        experience_match: Optional[float] = None,
        location_match: Optional[float] = None,
        salary_match: Optional[float] = None,
        culture_match: Optional[float] = None
    ) -> None:
        """
        Update analysis scores.
        
        Args:
            match_score: Overall match score
            confidence_score: Confidence in the analysis
            skill_match: Skills match score
            experience_match: Experience match score
            location_match: Location match score
            salary_match: Salary match score
            culture_match: Culture match score
        """
        if match_score is not None:
            self.match_score = max(0.0, min(1.0, match_score))
        
        if confidence_score is not None:
            self.confidence_score = max(0.0, min(1.0, confidence_score))
        
        if skill_match is not None:
            self.skill_match_score = max(0.0, min(1.0, skill_match))
        
        if experience_match is not None:
            self.experience_match_score = max(0.0, min(1.0, experience_match))
        
        if location_match is not None:
            self.location_match_score = max(0.0, min(1.0, location_match))
        
        if salary_match is not None:
            self.salary_match_score = max(0.0, min(1.0, salary_match))
        
        if culture_match is not None:
            self.culture_match_score = max(0.0, min(1.0, culture_match))
        
        self.updated_at = datetime.utcnow()
    
    def add_insight(self, category: str, insight: str, importance: str = "medium") -> None:
        """
        Add an insight to the analysis.
        
        Args:
            category: Insight category
            insight: Insight text
            importance: Importance level (high, medium, low)
        """
        if self.key_insights is None:
            self.key_insights = {}
        
        if category not in self.key_insights:
            self.key_insights[category] = []
        
        self.key_insights[category].append({
            "text": insight,
            "importance": importance,
            "added_at": datetime.utcnow().isoformat()
        })
        
        self.updated_at = datetime.utcnow()
    
    def add_recommendation(self, recommendation: str, action_type: str = "general") -> None:
        """
        Add a recommendation to the analysis.
        
        Args:
            recommendation: Recommendation text
            action_type: Type of action (apply, research, prepare, etc.)
        """
        if self.recommendations is None:
            self.recommendations = {}
        
        if action_type not in self.recommendations:
            self.recommendations[action_type] = []
        
        self.recommendations[action_type].append({
            "text": recommendation,
            "added_at": datetime.utcnow().isoformat()
        })
        
        self.updated_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str) -> None:
        """
        Mark analysis as failed.
        
        Args:
            error_message: Error message
        """
        self.status = "failed"
        self.error_message = error_message
        self.updated_at = datetime.utcnow()