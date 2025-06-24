"""
Analysis Repository Implementation

Repository for AI analysis-related database operations with advanced
filtering, aggregation, and analytics capabilities.
"""

from typing import List, Optional, Dict, Any, Type
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.base_repository import BaseRepository
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate, AnalysisUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisRepository(BaseRepository[Analysis, AnalysisCreate, AnalysisUpdate]):
    """Repository for analysis database operations."""
    
    @property
    def model(self) -> Type[Analysis]:
        return Analysis
    
    async def get_by_job_id(
        self,
        job_id: int,
        analysis_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Analysis]:
        """Get analyses for a specific job."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(self.model.job_id == job_id)
                
                if analysis_type:
                    query = query.where(self.model.analysis_type == analysis_type)
                
                if user_id:
                    query = query.where(self.model.user_id == user_id)
                
                query = query.order_by(self.model.created_at.desc())
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting analyses by job ID: {e}")
                return []
    
    async def get_latest_analysis(
        self,
        job_id: int,
        analysis_type: str = "job_match",
        user_id: Optional[str] = None
    ) -> Optional[Analysis]:
        """Get the latest analysis for a job."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.job_id == job_id,
                        self.model.analysis_type == analysis_type,
                        self.model.status == "completed"
                    )
                )
                
                if user_id:
                    query = query.where(self.model.user_id == user_id)
                
                query = query.order_by(self.model.created_at.desc()).limit(1)
                
                result = await session.execute(query)
                return result.scalar_one_or_none()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting latest analysis: {e}")
                return None
    
    async def get_high_match_analyses(
        self,
        min_score: float = 0.8,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Analysis]:
        """Get analyses with high match scores."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.match_score >= min_score,
                        self.model.status == "completed"
                    )
                )
                
                if user_id:
                    query = query.where(self.model.user_id == user_id)
                
                query = query.order_by(
                    self.model.match_score.desc(),
                    self.model.created_at.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting high match analyses: {e}")
                return []
    
    async def get_recent_analyses(
        self,
        days: int = 7,
        analysis_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Analysis]:
        """Get recent analyses."""
        async with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                query = select(self.model).where(
                    self.model.created_at >= cutoff_date
                )
                
                if analysis_type:
                    query = query.where(self.model.analysis_type == analysis_type)
                
                if user_id:
                    query = query.where(self.model.user_id == user_id)
                
                query = query.order_by(
                    self.model.created_at.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting recent analyses: {e}")
                return []
    
    async def get_pending_analyses(self, limit: int = 100) -> List[Analysis]:
        """Get analyses that are pending processing."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    self.model.status.in_(["pending", "processing"])
                ).order_by(self.model.created_at.asc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting pending analyses: {e}")
                return []
    
    async def get_failed_analyses(
        self,
        days: int = 1,
        limit: int = 50
    ) -> List[Analysis]:
        """Get failed analyses."""
        async with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                query = select(self.model).where(
                    and_(
                        self.model.status == "failed",
                        self.model.updated_at >= cutoff_date
                    )
                ).order_by(self.model.updated_at.desc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting failed analyses: {e}")
                return []
    
    async def get_analysis_with_job(self, analysis_id: int) -> Optional[Analysis]:
        """Get analysis with job data loaded."""
        async with self.get_session() as session:
            try:
                query = select(self.model).options(
                    selectinload(self.model.job)
                ).where(self.model.id == analysis_id)
                
                result = await session.execute(query)
                return result.scalar_one_or_none()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting analysis with job: {e}")
                return None
    
    async def search_analyses(
        self,
        query_text: Optional[str] = None,
        analysis_type: Optional[str] = None,
        min_match_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Analysis]:
        """Search analyses with multiple filters."""
        async with self.get_session() as session:
            try:
                query = select(self.model)
                conditions = []
                
                # Text search in results and insights
                if query_text:
                    search_term = f"%{query_text.lower()}%"
                    conditions.append(
                        or_(
                            self.model.results.astext.ilike(search_term),
                            self.model.key_insights.astext.ilike(search_term),
                            self.model.recommendations.astext.ilike(search_term)
                        )
                    )
                
                # Filter by analysis type
                if analysis_type:
                    conditions.append(self.model.analysis_type == analysis_type)
                
                # Filter by match score
                if min_match_score is not None:
                    conditions.append(self.model.match_score >= min_match_score)
                
                # Filter by confidence score
                if min_confidence is not None:
                    conditions.append(self.model.confidence_score >= min_confidence)
                
                # Filter by status
                if status:
                    conditions.append(self.model.status == status)
                
                # Filter by user
                if user_id:
                    conditions.append(self.model.user_id == user_id)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # Order by relevance
                query = query.order_by(
                    self.model.match_score.desc().nulls_last(),
                    self.model.confidence_score.desc(),
                    self.model.created_at.desc()
                )
                
                # Apply pagination
                query = query.offset(skip).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error searching analyses: {e}")
                return []
    
    async def get_analysis_statistics(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get analysis statistics and metrics."""
        async with self.get_session() as session:
            try:
                base_query = select(func.count(self.model.id))
                if user_id:
                    base_query = base_query.where(self.model.user_id == user_id)
                
                # Total analyses
                total_result = await session.execute(base_query)
                total_count = total_result.scalar() or 0
                
                # Completed analyses
                completed_result = await session.execute(
                    base_query.where(self.model.status == "completed")
                )
                completed_count = completed_result.scalar() or 0
                
                # Failed analyses
                failed_result = await session.execute(
                    base_query.where(self.model.status == "failed")
                )
                failed_count = failed_result.scalar() or 0
                
                # High match analyses (>= 0.8)
                high_match_result = await session.execute(
                    base_query.where(
                        and_(
                            self.model.status == "completed",
                            self.model.match_score >= 0.8
                        )
                    )
                )
                high_match_count = high_match_result.scalar() or 0
                
                # Recent analyses (last 7 days)
                cutoff_date = datetime.utcnow() - timedelta(days=7)
                recent_result = await session.execute(
                    base_query.where(self.model.created_at >= cutoff_date)
                )
                recent_count = recent_result.scalar() or 0
                
                # Average scores
                avg_scores_query = select(
                    func.avg(self.model.match_score).label('avg_match'),
                    func.avg(self.model.confidence_score).label('avg_confidence')
                ).where(self.model.status == "completed")
                
                if user_id:
                    avg_scores_query = avg_scores_query.where(self.model.user_id == user_id)
                
                avg_scores_result = await session.execute(avg_scores_query)
                avg_scores = avg_scores_result.first()
                
                # Analysis type breakdown
                type_breakdown_query = select(
                    self.model.analysis_type,
                    func.count(self.model.id).label('count')
                ).group_by(self.model.analysis_type)
                
                if user_id:
                    type_breakdown_query = type_breakdown_query.where(
                        self.model.user_id == user_id
                    )
                
                type_breakdown_result = await session.execute(type_breakdown_query)
                
                # AI model usage
                model_usage_query = select(
                    self.model.ai_model_used,
                    func.count(self.model.id).label('count')
                ).where(
                    self.model.ai_model_used.isnot(None)
                ).group_by(self.model.ai_model_used)
                
                if user_id:
                    model_usage_query = model_usage_query.where(
                        self.model.user_id == user_id
                    )
                
                model_usage_result = await session.execute(model_usage_query)
                
                return {
                    "total_analyses": total_count,
                    "completed_analyses": completed_count,
                    "failed_analyses": failed_count,
                    "high_match_analyses": high_match_count,
                    "recent_analyses": recent_count,
                    "success_rate": (completed_count / total_count * 100) if total_count > 0 else 0,
                    "high_match_rate": (high_match_count / completed_count * 100) if completed_count > 0 else 0,
                    "average_match_score": float(avg_scores.avg_match or 0),
                    "average_confidence_score": float(avg_scores.avg_confidence or 0),
                    "analysis_types": [
                        {"type": row.analysis_type, "count": row.count}
                        for row in type_breakdown_result.all()
                    ],
                    "ai_models_used": [
                        {"model": row.ai_model_used, "count": row.count}
                        for row in model_usage_result.all()
                    ]
                }
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting analysis statistics: {e}")
                return {}
    
    async def get_match_score_distribution(
        self,
        user_id: Optional[str] = None,
        analysis_type: str = "job_match"
    ) -> Dict[str, int]:
        """Get distribution of match scores."""
        async with self.get_session() as session:
            try:
                # Define score ranges
                score_ranges = [
                    ("excellent", 0.9, 1.0),
                    ("good", 0.7, 0.9),
                    ("fair", 0.5, 0.7),
                    ("poor", 0.0, 0.5)
                ]
                
                distribution = {}
                
                for range_name, min_score, max_score in score_ranges:
                    query = select(func.count(self.model.id)).where(
                        and_(
                            self.model.analysis_type == analysis_type,
                            self.model.status == "completed",
                            self.model.match_score >= min_score,
                            self.model.match_score < max_score
                        )
                    )
                    
                    if user_id:
                        query = query.where(self.model.user_id == user_id)
                    
                    result = await session.execute(query)
                    distribution[range_name] = result.scalar() or 0
                
                return distribution
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting match score distribution: {e}")
                return {}
    
    async def get_trending_insights(
        self,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending insights from analyses."""
        async with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # This is a simplified version - in production you'd want more sophisticated analysis
                query = select(
                    self.model.key_insights,
                    func.count(self.model.id).label('frequency')
                ).where(
                    and_(
                        self.model.created_at >= cutoff_date,
                        self.model.status == "completed",
                        self.model.key_insights.isnot(None)
                    )
                ).group_by(
                    self.model.key_insights
                ).order_by(
                    func.count(self.model.id).desc()
                ).limit(limit)
                
                result = await session.execute(query)
                
                trends = []
                for row in result.all():
                    if row.key_insights:
                        trends.append({
                            "insights": row.key_insights,
                            "frequency": row.frequency
                        })
                
                return trends
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting trending insights: {e}")
                return []
    
    async def cleanup_old_analyses(self, days_old: int = 90) -> int:
        """Remove old analyses to save space."""
        async with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                # Delete old analyses (keep completed ones with high scores)
                result = await session.execute(
                    text("""
                        DELETE FROM analyses 
                        WHERE created_at < :cutoff_date 
                        AND (
                            status != 'completed' 
                            OR match_score < 0.5 
                            OR match_score IS NULL
                        )
                    """),
                    {"cutoff_date": cutoff_date}
                )
                
                await session.commit()
                return result.rowcount
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error cleaning up old analyses: {e}")
                return 0
    
    async def update_analysis_status(
        self,
        analysis_id: int,
        status: str,
        error_message: Optional[str] = None,
        processing_time: Optional[float] = None
    ) -> Optional[Analysis]:
        """Update analysis processing status."""
        async with self.get_session() as session:
            try:
                analysis = await session.get(self.model, analysis_id)
                if not analysis:
                    return None
                
                analysis.status = status
                if error_message:
                    analysis.error_message = error_message
                if processing_time:
                    analysis.processing_time_seconds = processing_time
                
                await session.commit()
                await session.refresh(analysis)
                return analysis
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error updating analysis status: {e}")
                return None