"""
Job Management API Endpoints

Handles job-related operations including job search, filtering,
saving, and management functionality.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_db, 
    get_current_active_user, 
    get_optional_current_user,
    get_pagination, 
    Pagination,
    check_rate_limit,
    cache_helper,
    validation_helper
)
from app.models.job import Job
from app.models.company import Company
from app.schemas.job import (
    JobResponse, 
    JobCreate, 
    JobUpdate, 
    JobSearchParams,
    JobListResponse,
    JobAnalysisResponse
)
from app.services.job_matcher import JobMatcherService
from app.services.ai_analyzer import AIAnalyzerService
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter()

# Initialize services
job_matcher_service = JobMatcherService()
ai_analyzer_service = AIAnalyzerService()


@router.get("/jobs", response_model=JobListResponse)
async def get_jobs(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    pagination: Pagination = Depends(get_pagination),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    # Search parameters
    query: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None, description="Job location"),
    company: Optional[str] = Query(None, description="Company name"),
    salary_min: Optional[int] = Query(None, description="Minimum salary"),
    salary_max: Optional[int] = Query(None, description="Maximum salary"),
    job_type: Optional[str] = Query(None, description="Job type (full-time, part-time, etc.)"),
    experience_level: Optional[str] = Query(None, description="Experience level"),
    posted_days_ago: Optional[int] = Query(None, description="Posted within N days"),
    # Filters
    is_remote: Optional[bool] = Query(None, description="Remote jobs only"),
    has_salary: Optional[bool] = Query(None, description="Jobs with salary information"),
    exclude_viewed: Optional[bool] = Query(False, description="Exclude viewed jobs")
) -> JobListResponse:
    """
    Get paginated list of jobs with filtering and search.
    
    Args:
        background_tasks: Background tasks
        db: Database session
        pagination: Pagination parameters
        current_user: Current user (optional)
        query: Search query
        location: Location filter
        company: Company filter
        salary_min: Minimum salary filter
        salary_max: Maximum salary filter
        job_type: Job type filter
        experience_level: Experience level filter
        posted_days_ago: Posted within N days
        is_remote: Remote jobs filter
        has_salary: Jobs with salary filter
        exclude_viewed: Exclude viewed jobs
        
    Returns:
        JobListResponse: Paginated job list
    """
    # Validate search parameters
    search_params = validation_helper.validate_job_search_params(
        query=query,
        location=location,
        company=company,
        salary_min=salary_min,
        salary_max=salary_max
    )
    
    # Generate cache key
    cache_key = cache_helper.generate_cache_key(
        "jobs_list",
        page=pagination.page,
        size=pagination.size,
        **search_params,
        job_type=job_type,
        experience_level=experience_level,
        posted_days_ago=posted_days_ago,
        is_remote=is_remote,
        has_salary=has_salary,
        user_id=current_user.get("user_id") if current_user else None
    )
    
    # Check cache
    cached_response = await cache_helper.get_cached_response(cache_key)
    if cached_response:
        import json
        return JobListResponse(**json.loads(cached_response))
    
    try:
        # Build query
        query_stmt = select(Job).options(selectinload(Job.company))
        
        # Apply filters
        filters = []
        
        if search_params["query"]:
            search_term = f"%{search_params['query']}%"
            filters.append(
                or_(
                    Job.title.ilike(search_term),
                    Job.description.ilike(search_term),
                    Job.requirements.ilike(search_term)
                )
            )
        
        if search_params["location"]:
            location_term = f"%{search_params['location']}%"
            filters.append(Job.location.ilike(location_term))
        
        if search_params["company"]:
            company_term = f"%{search_params['company']}%"
            filters.append(Job.company.has(Company.name.ilike(company_term)))
        
        if search_params["salary_min"]:
            filters.append(Job.salary_min >= search_params["salary_min"])
        
        if search_params["salary_max"]:
            filters.append(Job.salary_max <= search_params["salary_max"])
        
        if job_type:
            filters.append(Job.job_type == job_type)
        
        if experience_level:
            filters.append(Job.experience_level == experience_level)
        
        if posted_days_ago:
            cutoff_date = datetime.utcnow() - timedelta(days=posted_days_ago)
            filters.append(Job.posted_date >= cutoff_date)
        
        if is_remote is not None:
            filters.append(Job.is_remote == is_remote)
        
        if has_salary is not None:
            if has_salary:
                filters.append(
                    or_(
                        Job.salary_min.is_not(None),
                        Job.salary_max.is_not(None)
                    )
                )
            else:
                filters.append(
                    and_(
                        Job.salary_min.is_(None),
                        Job.salary_max.is_(None)
                    )
                )
        
        # Apply filters
        if filters:
            query_stmt = query_stmt.where(and_(*filters))
        
        # Apply sorting
        if pagination.sort_by:
            sort_field = getattr(Job, pagination.sort_by, None)
            if sort_field:
                if pagination.sort_order == "asc":
                    query_stmt = query_stmt.order_by(asc(sort_field))
                else:
                    query_stmt = query_stmt.order_by(desc(sort_field))
        else:
            # Default sort by posted date
            query_stmt = query_stmt.order_by(desc(Job.posted_date))
        
        # Get total count
        count_stmt = select(func.count(Job.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        
        total_count = await db.scalar(count_stmt)
        
        # Apply pagination
        query_stmt = query_stmt.offset(pagination.offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(query_stmt)
        jobs = result.scalars().all()
        
        # Calculate pagination metadata
        total_pages = (total_count + pagination.size - 1) // pagination.size
        
        response = JobListResponse(
            jobs=[JobResponse.from_orm(job) for job in jobs],
            total_count=total_count,
            page=pagination.page,
            size=pagination.size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1
        )
        
        # Cache response for 5 minutes
        import json
        await cache_helper.set_cached_response(
            cache_key,
            json.dumps(response.dict(), default=str),
            expire_seconds=300
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve jobs"
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> JobResponse:
    """
    Get specific job by ID.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Current user (optional)
        
    Returns:
        JobResponse: Job details
        
    Raises:
        HTTPException: If job not found
    """
    try:
        # Get job with company details
        query = select(Job).options(selectinload(Job.company)).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Track job view if user is authenticated
        if current_user:
            # This would typically update a job_views table
            logger.info(f"User {current_user['user_id']} viewed job {job_id}")
        
        return JobResponse.from_orm(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job"
        )


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> JobResponse:
    """
    Create a new job posting.
    
    Args:
        job_data: Job creation data
        background_tasks: Background tasks
        db: Database session
        current_user: Current user
        
    Returns:
        JobResponse: Created job
    """
    try:
        # Create job instance
        job = Job(**job_data.dict(exclude_unset=True))
        job.created_by = current_user["user_id"]
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Schedule background analysis
        background_tasks.add_task(
            ai_analyzer_service.analyze_job,
            job.id
        )
        
        logger.info(f"Job {job.id} created by user {current_user['user_id']}")
        
        return JobResponse.from_orm(job)
        
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )


@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> JobResponse:
    """
    Update existing job.
    
    Args:
        job_id: Job ID
        job_data: Job update data
        db: Database session
        current_user: Current user
        
    Returns:
        JobResponse: Updated job
        
    Raises:
        HTTPException: If job not found or access denied
    """
    try:
        # Get existing job
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check permissions (simplified - in real app, check ownership/roles)
        # if job.created_by != current_user["user_id"]:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Not authorized to update this job"
        #     )
        
        # Update job fields
        update_data = job_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        job.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(job)
        
        logger.info(f"Job {job_id} updated by user {current_user['user_id']}")
        
        return JobResponse.from_orm(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job"
        )


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Delete job by ID.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Current user
        
    Returns:
        Dict[str, str]: Success message
        
    Raises:
        HTTPException: If job not found or access denied
    """
    try:
        # Get existing job
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check permissions
        # if job.created_by != current_user["user_id"]:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Not authorized to delete this job"
        #     )
        
        await db.delete(job)
        await db.commit()
        
        logger.info(f"Job {job_id} deleted by user {current_user['user_id']}")
        
        return {"message": "Job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete job"
        )


@router.post("/jobs/{job_id}/analyze", response_model=JobAnalysisResponse)
async def analyze_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> JobAnalysisResponse:
    """
    Analyze job with AI for match scoring and insights.
    
    Args:
        job_id: Job ID
        background_tasks: Background tasks
        db: Database session
        current_user: Current user
        
    Returns:
        JobAnalysisResponse: Job analysis results
        
    Raises:
        HTTPException: If job not found
    """
    try:
        # Get job
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Run AI analysis
        analysis = await ai_analyzer_service.analyze_job_for_user(
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        logger.info(f"Job {job_id} analyzed for user {current_user['user_id']}")
        
        return JobAnalysisResponse(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze job"
        )


@router.post("/jobs/match", response_model=List[JobResponse])
async def match_jobs(
    search_params: JobSearchParams,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    limit: int = Query(20, ge=1, le=100, description="Number of matches to return")
) -> List[JobResponse]:
    """
    Find job matches based on user preferences and criteria.
    
    Args:
        search_params: Job search parameters
        background_tasks: Background tasks
        db: Database session
        current_user: Current user
        limit: Number of matches to return
        
    Returns:
        List[JobResponse]: Matched jobs
    """
    try:
        # Get matched jobs
        matched_jobs = await job_matcher_service.find_job_matches(
            user_id=current_user["user_id"],
            search_params=search_params.dict(),
            limit=limit
        )
        
        logger.info(f"Found {len(matched_jobs)} job matches for user {current_user['user_id']}")
        
        return [JobResponse.from_orm(job) for job in matched_jobs]
        
    except Exception as e:
        logger.error(f"Error matching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match jobs"
        )