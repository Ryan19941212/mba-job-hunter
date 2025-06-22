"""
Job Pydantic Schemas

Request/response models for job-related API endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class JobBase(BaseModel):
    """Base job schema with common fields."""
    
    title: str = Field(..., min_length=1, max_length=500, description="Job title")
    description: Optional[str] = Field(None, description="Job description")
    requirements: Optional[str] = Field(None, description="Job requirements")
    responsibilities: Optional[str] = Field(None, description="Job responsibilities")
    
    location: Optional[str] = Field(None, max_length=200, description="Job location")
    is_remote: bool = Field(False, description="Whether job is remote")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    city: Optional[str] = Field(None, max_length=100, description="City")
    
    job_type: Optional[str] = Field(None, max_length=50, description="Job type (full-time, part-time, contract)")
    experience_level: Optional[str] = Field(None, max_length=50, description="Experience level")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    
    salary_min: Optional[Decimal] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[Decimal] = Field(None, ge=0, description="Maximum salary")
    salary_currency: str = Field("USD", max_length=10, description="Salary currency")
    salary_period: Optional[str] = Field(None, max_length=20, description="Salary period")
    
    skills_required: Optional[List[str]] = Field(None, description="Required skills")
    benefits: Optional[List[str]] = Field(None, description="Job benefits")


class JobCreate(JobBase):
    """Schema for creating a new job."""
    
    company_id: Optional[int] = Field(None, description="Company ID")
    source: Optional[str] = Field(None, max_length=50, description="Job source")
    source_job_id: Optional[str] = Field(None, max_length=200, description="Source job ID")
    source_url: Optional[str] = Field(None, max_length=1000, description="Source URL")
    posted_date: Optional[datetime] = Field(None, description="Job posting date")
    application_deadline: Optional[datetime] = Field(None, description="Application deadline")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional information")


class JobUpdate(BaseModel):
    """Schema for updating an existing job."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Job title")
    description: Optional[str] = Field(None, description="Job description")
    requirements: Optional[str] = Field(None, description="Job requirements")
    responsibilities: Optional[str] = Field(None, description="Job responsibilities")
    
    location: Optional[str] = Field(None, max_length=200, description="Job location")
    is_remote: Optional[bool] = Field(None, description="Whether job is remote")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    city: Optional[str] = Field(None, max_length=100, description="City")
    
    job_type: Optional[str] = Field(None, max_length=50, description="Job type")
    experience_level: Optional[str] = Field(None, max_length=50, description="Experience level")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    
    salary_min: Optional[Decimal] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[Decimal] = Field(None, ge=0, description="Maximum salary")
    salary_currency: Optional[str] = Field(None, max_length=10, description="Salary currency")
    salary_period: Optional[str] = Field(None, max_length=20, description="Salary period")
    
    skills_required: Optional[List[str]] = Field(None, description="Required skills")
    benefits: Optional[List[str]] = Field(None, description="Job benefits")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional information")
    
    is_active: Optional[bool] = Field(None, description="Whether job is active")


class CompanyInfo(BaseModel):
    """Basic company information for job responses."""
    
    id: int = Field(..., description="Company ID")
    name: str = Field(..., description="Company name")
    industry: Optional[str] = Field(None, description="Company industry")
    size: Optional[str] = Field(None, description="Company size")
    location: Optional[str] = Field(None, description="Company location")
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    glassdoor_rating: Optional[float] = Field(None, description="Glassdoor rating")


class JobResponse(BaseModel):
    """Schema for job response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    description: Optional[str] = Field(None, description="Job description")
    requirements: Optional[str] = Field(None, description="Job requirements")
    responsibilities: Optional[str] = Field(None, description="Job responsibilities")
    
    company_id: Optional[int] = Field(None, description="Company ID")
    company: Optional[CompanyInfo] = Field(None, description="Company information")
    
    location: Optional[str] = Field(None, description="Job location")
    is_remote: bool = Field(..., description="Whether job is remote")
    country: Optional[str] = Field(None, description="Country")
    state: Optional[str] = Field(None, description="State/Province")
    city: Optional[str] = Field(None, description="City")
    
    job_type: Optional[str] = Field(None, description="Job type")
    experience_level: Optional[str] = Field(None, description="Experience level")
    department: Optional[str] = Field(None, description="Department")
    
    salary_min: Optional[Decimal] = Field(None, description="Minimum salary")
    salary_max: Optional[Decimal] = Field(None, description="Maximum salary")
    salary_currency: str = Field(..., description="Salary currency")
    salary_period: Optional[str] = Field(None, description="Salary period")
    salary_range_display: Optional[str] = Field(None, description="Formatted salary range")
    
    source: Optional[str] = Field(None, description="Job source")
    source_job_id: Optional[str] = Field(None, description="Source job ID")
    source_url: Optional[str] = Field(None, description="Source URL")
    
    posted_date: Optional[datetime] = Field(None, description="Job posting date")
    application_deadline: Optional[datetime] = Field(None, description="Application deadline")
    
    skills_required: Optional[List[str]] = Field(None, description="Required skills")
    benefits: Optional[List[str]] = Field(None, description="Job benefits")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional information")
    
    is_active: bool = Field(..., description="Whether job is active")
    is_recent: bool = Field(..., description="Whether job is recent")
    has_salary_info: bool = Field(..., description="Whether job has salary info")
    application_count: int = Field(..., description="Application count")
    view_count: int = Field(..., description="View count")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Created by user ID")


class JobListResponse(BaseModel):
    """Schema for paginated job list response."""
    
    jobs: List[JobResponse] = Field(..., description="List of jobs")
    total_count: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class JobSearchParams(BaseModel):
    """Schema for job search parameters."""
    
    query: Optional[str] = Field(None, description="Search query")
    location: Optional[str] = Field(None, description="Location filter")
    company: Optional[str] = Field(None, description="Company filter")
    
    job_type: Optional[str] = Field(None, description="Job type filter")
    experience_level: Optional[str] = Field(None, description="Experience level filter")
    
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary")
    
    is_remote: Optional[bool] = Field(None, description="Remote jobs only")
    has_salary: Optional[bool] = Field(None, description="Jobs with salary info")
    
    posted_days_ago: Optional[int] = Field(None, ge=1, le=365, description="Posted within N days")
    
    skills: Optional[List[str]] = Field(None, description="Required skills")


class JobAnalysisResponse(BaseModel):
    """Schema for job analysis response."""
    
    job_id: int = Field(..., description="Job ID")
    analysis_id: int = Field(..., description="Analysis ID")
    
    match_score: float = Field(..., ge=0.0, le=1.0, description="Overall match score")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    
    skill_match_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Skills match score")
    experience_match_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Experience match score")
    location_match_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Location match score")
    salary_match_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Salary match score")
    culture_match_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Culture match score")
    
    match_level: str = Field(..., description="Match level (excellent, good, fair, poor)")
    confidence_level: str = Field(..., description="Confidence level (high, medium, low)")
    
    key_insights: Optional[Dict[str, Any]] = Field(None, description="Key insights")
    recommendations: Optional[Dict[str, Any]] = Field(None, description="Recommendations")
    red_flags: Optional[Dict[str, Any]] = Field(None, description="Red flags")
    
    analysis_summary: Optional[str] = Field(None, description="Analysis summary")
    
    created_at: datetime = Field(..., description="Analysis timestamp")


class JobMatchCriteria(BaseModel):
    """Schema for job matching criteria."""
    
    target_roles: List[str] = Field(..., description="Target job roles")
    preferred_locations: List[str] = Field(..., description="Preferred locations")
    salary_range: Optional[Dict[str, int]] = Field(None, description="Salary range preference")
    
    required_skills: List[str] = Field(..., description="Required skills")
    preferred_skills: Optional[List[str]] = Field(None, description="Preferred skills")
    
    experience_level: Optional[str] = Field(None, description="Experience level")
    company_sizes: Optional[List[str]] = Field(None, description="Preferred company sizes")
    industries: Optional[List[str]] = Field(None, description="Preferred industries")
    
    remote_preference: str = Field("hybrid", description="Remote work preference")
    
    exclude_keywords: Optional[List[str]] = Field(None, description="Keywords to exclude")


class JobSaveRequest(BaseModel):
    """Schema for saving a job."""
    
    notes: Optional[str] = Field(None, description="Personal notes about the job")
    priority: str = Field("medium", description="Priority level (high, medium, low)")
    application_status: str = Field("interested", description="Application status")
    remind_date: Optional[datetime] = Field(None, description="Reminder date")


class JobApplicationUpdate(BaseModel):
    """Schema for updating job application status."""
    
    status: str = Field(..., description="Application status")
    notes: Optional[str] = Field(None, description="Application notes")
    application_date: Optional[datetime] = Field(None, description="Application date")
    interview_date: Optional[datetime] = Field(None, description="Interview date")
    follow_up_date: Optional[datetime] = Field(None, description="Follow-up date")
    
