"""
Analysis API v1 Endpoints

AI-powered job analysis endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status

from app.services.analysis_service import AnalysisService
from app.schemas.analysis import AnalysisResponse, AnalysisCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/jobs/{job_id}/analyze", response_model=AnalysisResponse)
async def analyze_job(job_id: int):
    """Analyze job match for user."""
    try:
        analysis_service = AnalysisService()
        analysis = await analysis_service.analyze_job_basic(job_id)
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze job"
        )


@router.post("/", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(analysis_data: AnalysisCreate):
    """Create a new analysis."""
    try:
        analysis_service = AnalysisService()
        analysis = await analysis_service.create_analysis(analysis_data)
        return analysis
    except Exception as e:
        logger.error(f"Error creating analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create analysis"
        )


@router.get("/statistics")
async def get_analysis_statistics():
    """Get analysis statistics."""
    try:
        analysis_service = AnalysisService()
        stats = await analysis_service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting analysis statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis statistics"
        )