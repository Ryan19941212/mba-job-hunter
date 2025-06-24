"""
Job API v1 Endpoints

Simple RESTful API endpoints for job management.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.services.job_service import JobService
from app.schemas.job import JobResponse, JobCreate, JobUpdate, JobSearchParams
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get list of jobs."""
    try:
        job_service = JobService()
        jobs = await job_service.get_jobs(skip=skip, limit=limit)
        return jobs
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve jobs"
        )


@router.get("/search", response_model=List[JobResponse])
async def search_jobs(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    salary_min: Optional[int] = Query(None),
    remote_friendly: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Search jobs with filters."""
    try:
        search_params = JobSearchParams(
            query=query,
            location=location,
            salary_min=salary_min,
            remote_friendly=remote_friendly
        )
        
        job_service = JobService()
        jobs = await job_service.search_jobs(search_params, skip=skip, limit=limit)
        return jobs
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search jobs"
        )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int):
    """Get job by ID."""
    try:
        job_service = JobService()
        job = await job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job"
        )


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_data: JobCreate):
    """Create a new job."""
    try:
        job_service = JobService()
        job = await job_service.create_job(job_data)
        return job
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )


@router.get("/statistics/summary")
async def get_job_statistics():
    """Get job statistics and analytics."""
    try:
        job_service = JobService()
        stats = await job_service.get_job_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting job statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job statistics"
        )