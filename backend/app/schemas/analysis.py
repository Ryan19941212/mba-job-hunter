"""
Analysis Pydantic Schemas

Request/response models for AI analysis-related API endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, validator, ConfigDict


class AnalysisBase(BaseModel):
    """Base analysis schema with common fields."""
    
    analysis_type: str = Field(..., max_length=50, description="Type of analysis")
    results: Dict[str, Any] = Field(..., description="Analysis results")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    
    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        """Validate analysis type."""
        valid_types = [
            "job_match", "market_analysis", "trend_analysis", 
            "salary_analysis", "skill_gap", "company_analysis"
        ]
        if v not in valid_types:
            raise ValueError(f'Analysis type must be one of: {", ".join(valid_types)}')
        return v


class AnalysisCreate(AnalysisBase):
    """Schema for creating a new analysis."""
    
    job_id: Optional[int] = Field(None, description="Related job ID")
    analysis_version: str = Field("1.0", description="Analysis version")
    ai_model_used: Optional[str] = Field(None, description="AI model used")


class AnalysisUpdate(BaseModel):
    """Schema for updating an existing analysis."""
    
    results: Optional[Dict[str, Any]] = Field(None, description="Analysis results")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    match_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Match score")
    
    key_insights: Optional[Dict[str, Any]] = Field(None, description="Key insights")
    recommendations: Optional[Dict[str, Any]] = Field(None, description="Recommendations")
    red_flags: Optional[Dict[str, Any]] = Field(None, description="Red flags")
    
    status: Optional[str] = Field(None, description="Analysis status")


class AnalysisResponse(BaseModel):
    """Schema for analysis response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Analysis ID")
    job_id: Optional[int] = Field(None, description="Related job ID")
    user_id: Optional[str] = Field(None, description="User ID")
    
    analysis_type: str = Field(..., description="Type of analysis")
    analysis_version: str = Field(..., description="Analysis version")
    ai_model_used: Optional[str] = Field(None, description="AI model used")
    
    results: Dict[str, Any] = Field(..., description="Analysis results")
    
    confidence_score: float = Field(..., description="Confidence score")
    match_score: Optional[float] = Field(None, description="Match score")
    
    skill_match_score: Optional[float] = Field(None, description="Skills match score")
    experience_match_score: Optional[float] = Field(None, description="Experience match score")
    location_match_score: Optional[float] = Field(None, description="Location match score")
    salary_match_score: Optional[float] = Field(None, description="Salary match score")
    culture_match_score: Optional[float] = Field(None, description="Culture match score")
    
    key_insights: Optional[Dict[str, Any]] = Field(None, description="Key insights")
    recommendations: Optional[Dict[str, Any]] = Field(None, description="Recommendations")
    red_flags: Optional[Dict[str, Any]] = Field(None, description="Red flags")
    
    status: str = Field(..., description="Analysis status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")
    
    match_level: str = Field(..., description="Match level description")
    confidence_level: str = Field(..., description="Confidence level description")
    is_high_match: bool = Field(..., description="Whether this is a high match")
    is_good_match: bool = Field(..., description="Whether this is a good match")
    is_recent: bool = Field(..., description="Whether analysis is recent")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AnalysisListResponse(BaseModel):
    """Schema for paginated analysis list response."""
    
    analyses: List[AnalysisResponse] = Field(..., description="List of analyses")
    total_count: int = Field(..., description="Total number of analyses")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class JobMatchResponse(BaseModel):
    """Schema for job match response."""
    
    job_id: int = Field(..., description="Job ID")
    analysis_id: Optional[int] = Field(None, description="Analysis ID")
    
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    
    overall_match_score: float = Field(..., ge=0.0, le=1.0, description="Overall match score")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    
    skill_match_score: Optional[float] = Field(None, description="Skills match score")
    experience_match_score: Optional[float] = Field(None, description="Experience match score")
    location_match_score: Optional[float] = Field(None, description="Location match score")
    salary_match_score: Optional[float] = Field(None, description="Salary match score")
    culture_match_score: Optional[float] = Field(None, description="Culture match score")
    
    match_level: str = Field(..., description="Match level (excellent, good, fair, poor)")
    match_reasons: List[str] = Field(..., description="Reasons for match score")
    
    strengths: List[str] = Field(..., description="Job strengths for this candidate")
    concerns: List[str] = Field(..., description="Potential concerns")
    
    application_priority: str = Field(..., description="Application priority (high, medium, low)")
    estimated_success_rate: Optional[float] = Field(None, description="Estimated application success rate")
    
    next_steps: List[str] = Field(..., description="Recommended next steps")
    
    salary_analysis: Optional[Dict[str, Any]] = Field(None, description="Salary analysis")
    career_impact: Optional[Dict[str, Any]] = Field(None, description="Career impact analysis")
    
    created_at: datetime = Field(..., description="Match analysis timestamp")


class InsightResponse(BaseModel):
    """Schema for market insights response."""
    
    analysis_date: datetime = Field(..., description="Analysis date")
    location: Optional[str] = Field(None, description="Location analyzed")
    job_type: Optional[str] = Field(None, description="Job type analyzed")
    
    market_summary: str = Field(..., description="Market summary")
    
    total_jobs_analyzed: int = Field(..., description="Total jobs analyzed")
    avg_salary_range: Optional[Dict[str, float]] = Field(None, description="Average salary range")
    
    top_companies: List[Dict[str, Any]] = Field(..., description="Top hiring companies")
    top_skills: List[Dict[str, Any]] = Field(..., description="Most in-demand skills")
    top_locations: List[Dict[str, Any]] = Field(..., description="Top job locations")
    
    industry_breakdown: Dict[str, int] = Field(..., description="Jobs by industry")
    experience_level_breakdown: Dict[str, int] = Field(..., description="Jobs by experience level")
    company_size_breakdown: Dict[str, int] = Field(..., description="Jobs by company size")
    
    hiring_trends: List[Dict[str, Any]] = Field(..., description="Hiring trends over time")
    salary_trends: List[Dict[str, Any]] = Field(..., description="Salary trends")
    
    growth_opportunities: List[str] = Field(..., description="Market growth opportunities")
    competitive_landscape: List[str] = Field(..., description="Competitive landscape insights")
    
    recommendations: List[str] = Field(..., description="Market-based recommendations")
    
    data_freshness: str = Field(..., description="How recent the data is")


class TrendAnalysisResponse(BaseModel):
    """Schema for trend analysis response."""
    
    analysis_period: str = Field(..., description="Analysis period")
    metric: str = Field(..., description="Metric analyzed")
    
    trend_direction: str = Field(..., description="Trend direction (up, down, stable)")
    trend_strength: str = Field(..., description="Trend strength (strong, moderate, weak)")
    
    current_value: float = Field(..., description="Current metric value")
    previous_value: float = Field(..., description="Previous period value")
    change_percentage: float = Field(..., description="Percentage change")
    
    historical_data: List[Dict[str, Any]] = Field(..., description="Historical trend data")
    
    key_drivers: List[str] = Field(..., description="Key factors driving the trend")
    future_predictions: List[Dict[str, Any]] = Field(..., description="Future trend predictions")
    
    impact_analysis: str = Field(..., description="Impact analysis")
    implications: List[str] = Field(..., description="Implications for job seekers")
    
    recommendations: List[str] = Field(..., description="Trend-based recommendations")
    
    confidence_level: str = Field(..., description="Confidence in trend analysis")
    analysis_date: datetime = Field(..., description="Analysis date")


class SkillGapAnalysis(BaseModel):
    """Schema for skill gap analysis."""
    
    user_skills: List[str] = Field(..., description="User's current skills")
    target_role: str = Field(..., description="Target role")
    
    required_skills: List[str] = Field(..., description="Required skills for role")
    missing_skills: List[str] = Field(..., description="Skills user is missing")
    transferable_skills: List[str] = Field(..., description="Transferable skills")
    
    skill_gaps: List[Dict[str, Any]] = Field(..., description="Detailed skill gaps")
    learning_recommendations: List[Dict[str, Any]] = Field(..., description="Learning recommendations")
    
    priority_skills: List[str] = Field(..., description="High-priority skills to learn")
    time_estimates: Dict[str, str] = Field(..., description="Estimated time to learn skills")
    
    alternative_paths: List[Dict[str, Any]] = Field(..., description="Alternative career paths")
    
    overall_readiness: float = Field(..., ge=0.0, le=1.0, description="Overall role readiness score")
    readiness_level: str = Field(..., description="Readiness level description")


class SalaryAnalysisResponse(BaseModel):
    """Schema for salary analysis response."""
    
    role: str = Field(..., description="Job role")
    location: str = Field(..., description="Location")
    experience_level: str = Field(..., description="Experience level")
    
    market_salary_range: Dict[str, float] = Field(..., description="Market salary range")
    user_target_salary: Optional[float] = Field(None, description="User's target salary")
    
    percentile_ranking: Optional[float] = Field(None, description="Where target salary ranks")
    competitiveness: str = Field(..., description="Salary competitiveness")
    
    salary_factors: List[Dict[str, Any]] = Field(..., description="Factors affecting salary")
    comparison_data: Dict[str, Any] = Field(..., description="Salary comparison data")
    
    negotiation_tips: List[str] = Field(..., description="Salary negotiation tips")
    market_outlook: str = Field(..., description="Salary market outlook")
    
    similar_roles: List[Dict[str, Any]] = Field(..., description="Similar roles and salaries")
    
    analysis_date: datetime = Field(..., description="Analysis date")


class BatchAnalysisRequest(BaseModel):
    """Schema for batch analysis request."""
    
    job_ids: List[int] = Field(..., min_items=1, max_items=50, description="Job IDs to analyze")
    analysis_type: str = Field("job_match", description="Type of analysis")
    priority: str = Field("normal", description="Processing priority")
    
    @validator('job_ids')
    def validate_job_ids(cls, v):
        """Validate job IDs list."""
        if len(set(v)) != len(v):
            raise ValueError('Duplicate job IDs are not allowed')
        return v


class BatchAnalysisResponse(BaseModel):
    """Schema for batch analysis response."""
    
    batch_id: str = Field(..., description="Batch processing ID")
    total_jobs: int = Field(..., description="Total jobs to analyze")
    status: str = Field(..., description="Batch status")
    
    completed_count: int = Field(..., description="Completed analyses")
    failed_count: int = Field(..., description="Failed analyses")
    remaining_count: int = Field(..., description="Remaining analyses")
    
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion")
    
    results: List[AnalysisResponse] = Field(..., description="Completed analysis results")
    errors: List[Dict[str, Any]] = Field(..., description="Error details")
    
    created_at: datetime = Field(..., description="Batch creation time")
    updated_at: datetime = Field(..., description="Last update time")