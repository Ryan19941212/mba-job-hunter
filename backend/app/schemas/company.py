"""
Company Pydantic Schemas

Request/response models for company-related API endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, validator, HttpUrl, ConfigDict


class CompanyBase(BaseModel):
    """Base company schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=500, description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[HttpUrl] = Field(None, description="Company website")
    
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    size: Optional[str] = Field(None, max_length=50, description="Company size")
    type: Optional[str] = Field(None, max_length=50, description="Company type")
    founded_year: Optional[int] = Field(None, ge=1800, le=2024, description="Founded year")
    
    headquarters_location: Optional[str] = Field(None, max_length=200, description="HQ location")
    headquarters_country: Optional[str] = Field(None, max_length=100, description="HQ country")
    headquarters_state: Optional[str] = Field(None, max_length=100, description="HQ state")
    headquarters_city: Optional[str] = Field(None, max_length=100, description="HQ city")
    
    logo_url: Optional[HttpUrl] = Field(None, description="Company logo URL")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn URL")
    glassdoor_url: Optional[HttpUrl] = Field(None, description="Glassdoor URL")
    
    glassdoor_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Glassdoor rating")
    employee_count: Optional[int] = Field(None, ge=0, description="Employee count")
    
    tags: Optional[List[str]] = Field(None, description="Company tags")
    benefits: Optional[List[str]] = Field(None, description="Company benefits")
    culture_keywords: Optional[List[str]] = Field(None, description="Culture keywords")
    
    @validator('size')
    def validate_company_size(cls, v):
        """Validate company size."""
        if v is not None:
            valid_sizes = ["startup", "small", "medium", "large", "enterprise"]
            if v.lower() not in valid_sizes:
                raise ValueError(f'Company size must be one of: {", ".join(valid_sizes)}')
        return v
    
    @validator('type')
    def validate_company_type(cls, v):
        """Validate company type."""
        if v is not None:
            valid_types = ["public", "private", "non-profit", "government", "startup"]
            if v.lower() not in valid_types:
                raise ValueError(f'Company type must be one of: {", ".join(valid_types)}')
        return v


class CompanyCreate(CompanyBase):
    """Schema for creating a new company."""
    
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional information")


class CompanyUpdate(BaseModel):
    """Schema for updating an existing company."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=500, description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[HttpUrl] = Field(None, description="Company website")
    
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    size: Optional[str] = Field(None, max_length=50, description="Company size")
    type: Optional[str] = Field(None, max_length=50, description="Company type")
    founded_year: Optional[int] = Field(None, ge=1800, le=2024, description="Founded year")
    
    headquarters_location: Optional[str] = Field(None, max_length=200, description="HQ location")
    headquarters_country: Optional[str] = Field(None, max_length=100, description="HQ country")
    headquarters_state: Optional[str] = Field(None, max_length=100, description="HQ state")
    headquarters_city: Optional[str] = Field(None, max_length=100, description="HQ city")
    
    logo_url: Optional[HttpUrl] = Field(None, description="Company logo URL")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn URL")
    glassdoor_url: Optional[HttpUrl] = Field(None, description="Glassdoor URL")
    
    glassdoor_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Glassdoor rating")
    employee_count: Optional[int] = Field(None, ge=0, description="Employee count")
    
    tags: Optional[List[str]] = Field(None, description="Company tags")
    benefits: Optional[List[str]] = Field(None, description="Company benefits")
    culture_keywords: Optional[List[str]] = Field(None, description="Culture keywords")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional information")
    
    is_active: Optional[bool] = Field(None, description="Whether company is active")
    is_hiring: Optional[bool] = Field(None, description="Whether company is hiring")


class CompanyResponse(BaseModel):
    """Schema for company response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Company ID")
    name: str = Field(..., description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, description="Company website")
    
    industry: Optional[str] = Field(None, description="Industry")
    size: Optional[str] = Field(None, description="Company size")
    type: Optional[str] = Field(None, description="Company type")
    founded_year: Optional[int] = Field(None, description="Founded year")
    
    headquarters_location: Optional[str] = Field(None, description="HQ location")
    headquarters_country: Optional[str] = Field(None, description="HQ country")
    headquarters_state: Optional[str] = Field(None, description="HQ state")
    headquarters_city: Optional[str] = Field(None, description="HQ city")
    display_location: Optional[str] = Field(None, description="Formatted location")
    
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn URL")
    glassdoor_url: Optional[str] = Field(None, description="Glassdoor URL")
    
    glassdoor_rating: Optional[float] = Field(None, description="Glassdoor rating")
    employee_count: Optional[int] = Field(None, description="Employee count")
    
    tags: Optional[List[str]] = Field(None, description="Company tags")
    benefits: Optional[List[str]] = Field(None, description="Company benefits")
    culture_keywords: Optional[List[str]] = Field(None, description="Culture keywords")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional information")
    
    is_active: bool = Field(..., description="Whether company is active")
    is_hiring: bool = Field(..., description="Whether company is hiring")
    job_count: int = Field(..., description="Current job count")
    
    company_age: Optional[int] = Field(None, description="Company age in years")
    is_startup: bool = Field(..., description="Whether company is a startup")
    has_good_rating: bool = Field(..., description="Whether company has good rating")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class CompanyListResponse(BaseModel):
    """Schema for paginated company list response."""
    
    companies: List[CompanyResponse] = Field(..., description="List of companies")
    total_count: int = Field(..., description="Total number of companies")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class CompanySearchParams(BaseModel):
    """Schema for company search parameters."""
    
    query: Optional[str] = Field(None, description="Search query")
    industry: Optional[str] = Field(None, description="Industry filter")
    size: Optional[str] = Field(None, description="Company size filter")
    type: Optional[str] = Field(None, description="Company type filter")
    location: Optional[str] = Field(None, description="Location filter")
    
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Minimum rating")
    is_hiring: Optional[bool] = Field(None, description="Currently hiring filter")
    has_jobs: Optional[bool] = Field(None, description="Has active jobs filter")
    
    founded_after: Optional[int] = Field(None, ge=1800, description="Founded after year")
    founded_before: Optional[int] = Field(None, le=2024, description="Founded before year")
    
    tags: Optional[List[str]] = Field(None, description="Company tags filter")


class CompanyStatsResponse(BaseModel):
    """Schema for company statistics response."""
    
    company_id: int = Field(..., description="Company ID")
    company_name: str = Field(..., description="Company name")
    
    total_jobs: int = Field(..., description="Total jobs posted")
    active_jobs: int = Field(..., description="Currently active jobs")
    recent_jobs: int = Field(..., description="Jobs posted in last 30 days")
    
    avg_salary_min: Optional[float] = Field(None, description="Average minimum salary")
    avg_salary_max: Optional[float] = Field(None, description="Average maximum salary")
    
    job_types: Dict[str, int] = Field(..., description="Job types breakdown")
    experience_levels: Dict[str, int] = Field(..., description="Experience levels breakdown")
    locations: Dict[str, int] = Field(..., description="Job locations breakdown")
    
    top_skills: List[Dict[str, Any]] = Field(..., description="Most required skills")
    
    hiring_trend: List[Dict[str, Any]] = Field(..., description="Hiring trend over time")
    
    last_updated: datetime = Field(..., description="Statistics last updated")


class CompanyAnalysisResponse(BaseModel):
    """Schema for company analysis response."""
    
    company_id: int = Field(..., description="Company ID")
    analysis_date: datetime = Field(..., description="Analysis date")
    
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall company score")
    
    growth_score: float = Field(..., ge=0.0, le=1.0, description="Growth potential score")
    culture_score: float = Field(..., ge=0.0, le=1.0, description="Culture score")
    compensation_score: float = Field(..., ge=0.0, le=1.0, description="Compensation score")
    opportunity_score: float = Field(..., ge=0.0, le=1.0, description="Career opportunity score")
    
    strengths: List[str] = Field(..., description="Company strengths")
    weaknesses: List[str] = Field(..., description="Company weaknesses")
    opportunities: List[str] = Field(..., description="Growth opportunities")
    
    market_position: str = Field(..., description="Market position analysis")
    competitive_advantages: List[str] = Field(..., description="Competitive advantages")
    
    salary_competitiveness: str = Field(..., description="Salary competitiveness")
    benefits_quality: str = Field(..., description="Benefits quality assessment")
    
    recommendation: str = Field(..., description="Overall recommendation")
    recommendation_reason: str = Field(..., description="Reason for recommendation")
    
    similar_companies: List[Dict[str, Any]] = Field(..., description="Similar companies")


class CompanyReviewSummary(BaseModel):
    """Schema for company review summary."""
    
    company_id: int = Field(..., description="Company ID")
    
    glassdoor_rating: Optional[float] = Field(None, description="Glassdoor rating")
    glassdoor_reviews_count: Optional[int] = Field(None, description="Number of Glassdoor reviews")
    
    linkedin_followers: Optional[int] = Field(None, description="LinkedIn followers")
    
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Overall sentiment score")
    
    positive_aspects: List[str] = Field(..., description="Positive aspects mentioned")
    negative_aspects: List[str] = Field(..., description="Negative aspects mentioned")
    
    common_praise: List[str] = Field(..., description="Common praise themes")
    common_complaints: List[str] = Field(..., description="Common complaint themes")
    
    work_life_balance_rating: Optional[float] = Field(None, description="Work-life balance rating")
    career_opportunities_rating: Optional[float] = Field(None, description="Career opportunities rating")
    compensation_rating: Optional[float] = Field(None, description="Compensation rating")
    management_rating: Optional[float] = Field(None, description="Management rating")
    
    last_updated: datetime = Field(..., description="Reviews last updated")