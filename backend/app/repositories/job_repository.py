"""
Job Repository Implementation

Repository for job-related database operations with advanced filtering,
search capabilities, and analytics support.
"""

from typing import List, Optional, Dict, Any, Type
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.base_repository import BaseRepository
from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate, JobSearchParams
from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobRepository(BaseRepository[Job, JobCreate, JobUpdate]):
    """Repository for job database operations."""
    
    @property
    def model(self) -> Type[Job]:
        return Job
    
    async def get_by_source_url(self, source_url: str) -> Optional[Job]:
        """Get job by source URL to prevent duplicates."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(self.model.source_url == source_url)
                result = await session.execute(query)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                logger.error(f"Error getting job by source URL: {e}")
                return None
    
    async def search_jobs(
        self,
        search_params: JobSearchParams,
        skip: int = 0,
        limit: int = 100
    ) -> List[Job]:
        """Advanced job search with filtering."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(self.model.is_active == True)
                
                # Text search across title, company, and description
                if search_params.query:
                    search_term = f"%{search_params.query.lower()}%"
                    query = query.where(
                        or_(
                            func.lower(self.model.title).contains(search_term),
                            func.lower(self.model.company_name).contains(search_term),
                            func.lower(self.model.description).contains(search_term)
                        )
                    )
                
                # Location filter
                if search_params.location:
                    location_term = f"%{search_params.location.lower()}%"
                    query = query.where(
                        func.lower(self.model.location).contains(location_term)
                    )
                
                # Company filter
                if search_params.company:
                    company_term = f"%{search_params.company.lower()}%"
                    query = query.where(
                        func.lower(self.model.company_name).contains(company_term)
                    )
                
                # Job type filter
                if search_params.job_type:
                    query = query.where(self.model.employment_type == search_params.job_type)
                
                # Salary range filter
                if search_params.salary_min is not None:
                    query = query.where(
                        or_(
                            self.model.salary_min >= search_params.salary_min,
                            self.model.salary_max >= search_params.salary_min
                        )
                    )
                
                if search_params.salary_max is not None:
                    query = query.where(
                        or_(
                            self.model.salary_max <= search_params.salary_max,
                            self.model.salary_min <= search_params.salary_max
                        )
                    )
                
                # Remote work filter
                if search_params.is_remote is not None:
                    query = query.where(self.model.remote_friendly == search_params.is_remote)
                
                # Salary info availability filter
                if search_params.has_salary:
                    query = query.where(
                        or_(
                            self.model.salary_min.isnot(None),
                            self.model.salary_max.isnot(None)
                        )
                    )
                
                # Posted date filter
                if search_params.posted_days_ago is not None:
                    cutoff_date = datetime.utcnow() - timedelta(days=search_params.posted_days_ago)
                    query = query.where(self.model.posted_date >= cutoff_date)
                
                # Skills filter
                if search_params.skills:
                    for skill in search_params.skills:
                        skill_term = f"%{skill.lower()}%"
                        query = query.where(
                            or_(
                                func.lower(self.model.description).contains(skill_term),
                                func.lower(self.model.requirements).contains(skill_term),
                                self.model.extracted_skills.any(skill)
                            )
                        )
                
                # Order by relevance and date
                query = query.order_by(
                    self.model.posted_date.desc(),
                    self.model.created_at.desc()
                )
                
                # Apply pagination
                query = query.offset(skip).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error searching jobs: {e}")
                return []
    
    async def get_jobs_by_company(
        self,
        company_name: str,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Job]:
        """Get jobs by company name."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    func.lower(self.model.company_name) == company_name.lower()
                )
                
                if active_only:
                    query = query.where(self.model.is_active == True)
                
                query = query.order_by(self.model.posted_date.desc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting jobs by company: {e}")
                return []
    
    async def get_recent_jobs(
        self,
        days: int = 7,
        limit: int = 100
    ) -> List[Job]:
        """Get recently posted jobs."""
        async with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                query = select(self.model).where(
                    and_(
                        self.model.is_active == True,
                        self.model.posted_date >= cutoff_date
                    )
                ).order_by(self.model.posted_date.desc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting recent jobs: {e}")
                return []
    
    async def get_high_scoring_jobs(
        self,
        min_score: int = 70,
        limit: int = 50
    ) -> List[Job]:
        """Get jobs with high AI fit scores."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.is_active == True,
                        self.model.ai_fit_score >= min_score
                    )
                ).order_by(self.model.ai_fit_score.desc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting high scoring jobs: {e}")
                return []
    
    async def get_remote_jobs(self, limit: int = 100) -> List[Job]:
        """Get remote-friendly jobs."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.is_active == True,
                        self.model.remote_friendly == True
                    )
                ).order_by(self.model.posted_date.desc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting remote jobs: {e}")
                return []
    
    async def get_jobs_by_platform(
        self,
        platform: str,
        active_only: bool = True,
        limit: int = 100
    ) -> List[Job]:
        """Get jobs by source platform."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    self.model.source_platform == platform
                )
                
                if active_only:
                    query = query.where(self.model.is_active == True)
                
                query = query.order_by(self.model.created_at.desc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting jobs by platform: {e}")
                return []
    
    async def get_jobs_needing_analysis(self, limit: int = 50) -> List[Job]:
        """Get jobs that need AI analysis."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.is_active == True,
                        self.model.ai_fit_score.is_(None)
                    )
                ).order_by(self.model.created_at.asc()).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting jobs needing analysis: {e}")
                return []
    
    async def update_ai_analysis(
        self,
        job_id: int,
        fit_score: int,
        summary: str,
        skills: List[str]
    ) -> Optional[Job]:
        """Update AI analysis results for a job."""
        async with self.get_session() as session:
            try:
                job = await session.get(self.model, job_id)
                if not job:
                    return None
                
                job.ai_fit_score = fit_score
                job.ai_summary = summary
                job.extracted_skills = skills
                
                await session.commit()
                await session.refresh(job)
                return job
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error updating AI analysis for job {job_id}: {e}")
                return None
    
    async def get_job_statistics(self) -> Dict[str, Any]:
        """Get job statistics and analytics."""
        async with self.get_session() as session:
            try:
                # Total jobs
                total_jobs = await session.execute(
                    select(func.count(self.model.id))
                )
                total_count = total_jobs.scalar() or 0
                
                # Active jobs
                active_jobs = await session.execute(
                    select(func.count(self.model.id)).where(self.model.is_active == True)
                )
                active_count = active_jobs.scalar() or 0
                
                # Recent jobs (last 7 days)
                cutoff_date = datetime.utcnow() - timedelta(days=7)
                recent_jobs = await session.execute(
                    select(func.count(self.model.id)).where(
                        and_(
                            self.model.is_active == True,
                            self.model.posted_date >= cutoff_date
                        )
                    )
                )
                recent_count = recent_jobs.scalar() or 0
                
                # Jobs with salary info
                salary_jobs = await session.execute(
                    select(func.count(self.model.id)).where(
                        and_(
                            self.model.is_active == True,
                            or_(
                                self.model.salary_min.isnot(None),
                                self.model.salary_max.isnot(None)
                            )
                        )
                    )
                )
                salary_count = salary_jobs.scalar() or 0
                
                # Remote jobs
                remote_jobs = await session.execute(
                    select(func.count(self.model.id)).where(
                        and_(
                            self.model.is_active == True,
                            self.model.remote_friendly == True
                        )
                    )
                )
                remote_count = remote_jobs.scalar() or 0
                
                # Top companies by job count
                top_companies = await session.execute(
                    select(
                        self.model.company_name,
                        func.count(self.model.id).label('job_count')
                    ).where(
                        self.model.is_active == True
                    ).group_by(
                        self.model.company_name
                    ).order_by(
                        func.count(self.model.id).desc()
                    ).limit(10)
                )
                
                # Top locations by job count
                top_locations = await session.execute(
                    select(
                        self.model.location,
                        func.count(self.model.id).label('job_count')
                    ).where(
                        and_(
                            self.model.is_active == True,
                            self.model.location.isnot(None)
                        )
                    ).group_by(
                        self.model.location
                    ).order_by(
                        func.count(self.model.id).desc()
                    ).limit(10)
                )
                
                return {
                    "total_jobs": total_count,
                    "active_jobs": active_count,
                    "recent_jobs": recent_count,
                    "jobs_with_salary": salary_count,
                    "remote_jobs": remote_count,
                    "top_companies": [
                        {"name": row.company_name, "job_count": row.job_count}
                        for row in top_companies.all()
                    ],
                    "top_locations": [
                        {"location": row.location, "job_count": row.job_count}
                        for row in top_locations.all()
                    ]
                }
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting job statistics: {e}")
                return {}
    
    async def cleanup_expired_jobs(self, days_old: int = 30) -> int:
        """Mark old jobs as inactive."""
        async with self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                # Update old jobs to inactive
                result = await session.execute(
                    text("""
                        UPDATE jobs 
                        SET is_active = false, updated_at = CURRENT_TIMESTAMP
                        WHERE is_active = true 
                        AND (posted_date < :cutoff_date OR created_at < :cutoff_date)
                    """),
                    {"cutoff_date": cutoff_date}
                )
                
                await session.commit()
                return result.rowcount
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error cleaning up expired jobs: {e}")
                return 0
    
    async def duplicate_check(self, title: str, company_name: str, source_url: str) -> bool:
        """Check if a job is a potential duplicate."""
        async with self.get_session() as session:
            try:
                # Check for exact URL match
                url_query = select(func.count(self.model.id)).where(
                    self.model.source_url == source_url
                )
                url_result = await session.execute(url_query)
                if (url_result.scalar() or 0) > 0:
                    return True
                
                # Check for similar title and company
                similar_query = select(func.count(self.model.id)).where(
                    and_(
                        func.lower(self.model.title) == title.lower(),
                        func.lower(self.model.company_name) == company_name.lower(),
                        self.model.is_active == True
                    )
                )
                similar_result = await session.execute(similar_query)
                return (similar_result.scalar() or 0) > 0
                
            except SQLAlchemyError as e:
                logger.error(f"Error checking for duplicates: {e}")
                return False