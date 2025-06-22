"""
Job Analysis API Endpoints

Handles AI-powered job analysis, matching, and insights generation
for the MBA Job Hunter application.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.api.deps import (
    get_db, 
    get_current_active_user,
    get_pagination,
    Pagination,
    cache_helper
)
from app.models.job import Job
from app.models.analysis import Analysis
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisCreate,
    AnalysisListResponse,
    JobMatchResponse,
    InsightResponse,
    TrendAnalysisResponse
)
from app.services.ai_analyzer import AIAnalyzerService
from app.services.job_matcher import JobMatcherService
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter()

# Initialize services
ai_analyzer_service = AIAnalyzerService()
job_matcher_service = JobMatcherService()


@router.get("/analysis", response_model=AnalysisListResponse)
async def get_user_analyses(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    pagination: Pagination = Depends(get_pagination),
    analysis_type: Optional[str] = Query(None, description="Filter by analysis type"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)")
) -> AnalysisListResponse:
    """
    Get paginated list of user's job analyses.
    
    Args:
        db: Database session
        current_user: Current user
        pagination: Pagination parameters
        analysis_type: Filter by analysis type
        start_date: Start date filter
        end_date: End date filter
        
    Returns:
        AnalysisListResponse: Paginated analysis list
    """
    try:
        # Build query for user's analyses
        query = select(Analysis).where(Analysis.user_id == current_user["user_id"])
        
        # Apply filters
        filters = []
        
        if analysis_type:
            filters.append(Analysis.analysis_type == analysis_type)
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            filters.append(Analysis.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            filters.append(Analysis.created_at <= end_dt)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply sorting
        if pagination.sort_by and hasattr(Analysis, pagination.sort_by):
            sort_field = getattr(Analysis, pagination.sort_by)
            if pagination.sort_order == "asc":
                query = query.order_by(sort_field.asc())
            else:
                query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(desc(Analysis.created_at))
        
        # Get total count
        count_query = select(func.count(Analysis.id)).where(
            Analysis.user_id == current_user["user_id"]
        )
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(query)
        analyses = result.scalars().all()
        
        # Calculate pagination metadata
        total_pages = (total_count + pagination.size - 1) // pagination.size
        
        return AnalysisListResponse(
            analyses=[AnalysisResponse.from_orm(analysis) for analysis in analyses],
            total_count=total_count,
            page=pagination.page,
            size=pagination.size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1
        )
        
    except Exception as e:
        logger.error(f"Error retrieving analyses for user {current_user['user_id']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analyses"
        )


@router.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> AnalysisResponse:
    """
    Get specific analysis by ID.
    
    Args:
        analysis_id: Analysis ID
        db: Database session
        current_user: Current user
        
    Returns:
        AnalysisResponse: Analysis details
        
    Raises:
        HTTPException: If analysis not found or access denied
    """
    try:
        query = select(Analysis).where(
            and_(
                Analysis.id == analysis_id,
                Analysis.user_id == current_user["user_id"]
            )
        )
        result = await db.execute(query)
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        return AnalysisResponse.from_orm(analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis"
        )


@router.post("/analysis/job/{job_id}", response_model=AnalysisResponse)
async def analyze_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    force_reanalysis: bool = Query(False, description="Force re-analysis even if exists")
) -> AnalysisResponse:
    """
    Analyze a specific job for the current user.
    
    Args:
        job_id: Job ID to analyze
        background_tasks: Background tasks
        db: Database session
        current_user: Current user
        force_reanalysis: Force re-analysis
        
    Returns:
        AnalysisResponse: Analysis results
        
    Raises:
        HTTPException: If job not found
    """
    try:
        # Check if job exists
        job_query = select(Job).where(Job.id == job_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if analysis already exists
        if not force_reanalysis:
            existing_query = select(Analysis).where(
                and_(
                    Analysis.job_id == job_id,
                    Analysis.user_id == current_user["user_id"],
                    Analysis.analysis_type == "job_match"
                )
            )
            existing_result = await db.execute(existing_query)
            existing_analysis = existing_result.scalar_one_or_none()
            
            if existing_analysis:
                return AnalysisResponse.from_orm(existing_analysis)
        
        # Perform analysis
        analysis_result = await ai_analyzer_service.analyze_job_for_user(
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        # Save analysis to database
        analysis = Analysis(
            job_id=job_id,
            user_id=current_user["user_id"],
            analysis_type="job_match",
            results=analysis_result,
            confidence_score=analysis_result.get("confidence_score", 0.0)
        )
        
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        
        logger.info(f"Job {job_id} analyzed for user {current_user['user_id']}")
        
        return AnalysisResponse.from_orm(analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing job {job_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze job"
        )


@router.post("/analysis/batch", response_model=List[AnalysisResponse])
async def analyze_jobs_batch(
    job_ids: List[int],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> List[AnalysisResponse]:
    """
    Analyze multiple jobs in batch for the current user.
    
    Args:
        job_ids: List of job IDs to analyze
        background_tasks: Background tasks
        db: Database session
        current_user: Current user
        
    Returns:
        List[AnalysisResponse]: Analysis results
        
    Raises:
        HTTPException: If validation fails
    """
    if len(job_ids) > 50:  # Limit batch size
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size cannot exceed 50 jobs"
        )
    
    try:
        # Verify all jobs exist
        jobs_query = select(Job.id).where(Job.id.in_(job_ids))
        jobs_result = await db.execute(jobs_query)
        existing_job_ids = {row[0] for row in jobs_result.fetchall()}
        
        missing_job_ids = set(job_ids) - existing_job_ids
        if missing_job_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Jobs not found: {list(missing_job_ids)}"
            )
        
        # Schedule batch analysis as background task
        background_tasks.add_task(
            ai_analyzer_service.analyze_jobs_batch,
            job_ids=list(existing_job_ids),
            user_id=current_user["user_id"]
        )
        
        # Return placeholder response indicating processing started
        analyses = []
        for job_id in existing_job_ids:
            analyses.append(AnalysisResponse(
                id=0,  # Placeholder
                job_id=job_id,
                user_id=current_user["user_id"],
                analysis_type="job_match",
                results={"status": "processing"},
                confidence_score=0.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ))
        
        logger.info(f"Batch analysis started for {len(job_ids)} jobs for user {current_user['user_id']}")
        
        return analyses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch job analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start batch analysis"
        )


@router.get("/analysis/matches", response_model=List[JobMatchResponse])
async def get_job_matches(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    min_score: float = Query(0.7, ge=0.0, le=1.0, description="Minimum match score"),
    limit: int = Query(20, ge=1, le=100, description="Number of matches to return")
) -> List[JobMatchResponse]:
    """
    Get job matches for the current user based on their profile and preferences.
    
    Args:
        db: Database session
        current_user: Current user
        min_score: Minimum match score
        limit: Number of matches to return
        
    Returns:
        List[JobMatchResponse]: Job matches
    """
    try:
        # Get job matches from service
        matches = await job_matcher_service.get_user_job_matches(
            user_id=current_user["user_id"],
            min_score=min_score,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(matches)} job matches for user {current_user['user_id']}")
        
        return matches
        
    except Exception as e:
        logger.error(f"Error retrieving job matches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job matches"
        )


@router.get("/analysis/insights", response_model=InsightResponse)
async def get_job_market_insights(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    location: Optional[str] = Query(None, description="Location filter"),
    job_type: Optional[str] = Query(None, description="Job type filter"),
    days_back: int = Query(30, ge=1, le=365, description="Days to look back for insights")
) -> InsightResponse:
    """
    Get job market insights and trends.
    
    Args:
        db: Database session
        current_user: Current user
        location: Location filter
        job_type: Job type filter
        days_back: Days to look back
        
    Returns:
        InsightResponse: Market insights
    """
    cache_key = cache_helper.generate_cache_key(
        "market_insights",
        location=location,
        job_type=job_type,
        days_back=days_back
    )
    
    # Check cache
    cached_insights = await cache_helper.get_cached_response(cache_key)
    if cached_insights:
        import json
        return InsightResponse(**json.loads(cached_insights))
    
    try:
        # Generate insights
        insights = await ai_analyzer_service.generate_market_insights(
            location=location,
            job_type=job_type,
            days_back=days_back
        )
        
        # Cache insights for 1 hour
        import json
        await cache_helper.set_cached_response(
            cache_key,
            json.dumps(insights, default=str),
            expire_seconds=3600
        )
        
        logger.info(f"Generated market insights for user {current_user['user_id']}")
        
        return InsightResponse(**insights)
        
    except Exception as e:
        logger.error(f"Error generating market insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate market insights"
        )


@router.get("/analysis/trends", response_model=TrendAnalysisResponse)
async def get_job_trends(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    period: str = Query("month", regex="^(week|month|quarter|year)$", description="Analysis period"),
    metric: str = Query("job_count", description="Metric to analyze")
) -> TrendAnalysisResponse:
    """
    Get job market trend analysis.
    
    Args:
        db: Database session
        current_user: Current user
        period: Analysis period
        metric: Metric to analyze
        
    Returns:
        TrendAnalysisResponse: Trend analysis
    """
    cache_key = cache_helper.generate_cache_key(
        "job_trends",
        period=period,
        metric=metric
    )
    
    # Check cache
    cached_trends = await cache_helper.get_cached_response(cache_key)
    if cached_trends:
        import json
        return TrendAnalysisResponse(**json.loads(cached_trends))
    
    try:
        # Generate trend analysis
        trends = await ai_analyzer_service.analyze_job_trends(
            period=period,
            metric=metric
        )
        
        # Cache trends for 30 minutes
        import json
        await cache_helper.set_cached_response(
            cache_key,
            json.dumps(trends, default=str),
            expire_seconds=1800
        )
        
        logger.info(f"Generated trend analysis for user {current_user['user_id']}")
        
        return TrendAnalysisResponse(**trends)
        
    except Exception as e:
        logger.error(f"Error analyzing job trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze job trends"
        )


@router.delete("/analysis/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Delete analysis by ID.
    
    Args:
        analysis_id: Analysis ID
        db: Database session
        current_user: Current user
        
    Returns:
        Dict[str, str]: Success message
        
    Raises:
        HTTPException: If analysis not found or access denied
    """
    try:
        query = select(Analysis).where(
            and_(
                Analysis.id == analysis_id,
                Analysis.user_id == current_user["user_id"]
            )
        )
        result = await db.execute(query)
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        await db.delete(analysis)
        await db.commit()
        
        logger.info(f"Analysis {analysis_id} deleted by user {current_user['user_id']}")
        
        return {"message": "Analysis deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis {analysis_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete analysis"
        )