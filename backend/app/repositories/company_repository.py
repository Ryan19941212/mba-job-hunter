"""
Company Repository Implementation

Repository for company-related database operations with search,
analytics, and relationship management capabilities.
"""

from typing import List, Optional, Dict, Any, Type
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.base_repository import BaseRepository
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanySearchParams
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CompanyRepository(BaseRepository[Company, CompanyCreate, CompanyUpdate]):
    """Repository for company database operations."""
    
    @property
    def model(self) -> Type[Company]:
        return Company
    
    async def get_by_name(self, name: str) -> Optional[Company]:
        """Get company by exact name match."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    func.lower(self.model.name) == name.lower()
                )
                result = await session.execute(query)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                logger.error(f"Error getting company by name: {e}")
                return None
    
    async def search_companies(
        self,
        search_params: CompanySearchParams,
        skip: int = 0,
        limit: int = 100
    ) -> List[Company]:
        """Advanced company search with filtering."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(self.model.is_active == True)
                
                # Text search across name and description
                if search_params.query:
                    search_term = f"%{search_params.query.lower()}%"
                    query = query.where(
                        or_(
                            func.lower(self.model.name).contains(search_term),
                            func.lower(self.model.description).contains(search_term)
                        )
                    )
                
                # Industry filter
                if search_params.industry:
                    query = query.where(
                        func.lower(self.model.industry).contains(
                            search_params.industry.lower()
                        )
                    )
                
                # Size filter
                if search_params.size:
                    query = query.where(self.model.size == search_params.size)
                
                # Type filter
                if search_params.type:
                    query = query.where(self.model.type == search_params.type)
                
                # Location filter
                if search_params.location:
                    location_term = f"%{search_params.location.lower()}%"
                    query = query.where(
                        or_(
                            func.lower(self.model.headquarters_location).contains(location_term),
                            func.lower(self.model.headquarters_country).contains(location_term),
                            func.lower(self.model.headquarters_state).contains(location_term),
                            func.lower(self.model.headquarters_city).contains(location_term)
                        )
                    )
                
                # Rating filter
                if search_params.min_rating is not None:
                    query = query.where(
                        self.model.glassdoor_rating >= search_params.min_rating
                    )
                
                # Hiring status filter
                if search_params.is_hiring is not None:
                    query = query.where(self.model.is_hiring == search_params.is_hiring)
                
                # Has jobs filter
                if search_params.has_jobs:
                    query = query.where(self.model.job_count > 0)
                
                # Founded year filters
                if search_params.founded_after is not None:
                    query = query.where(
                        self.model.founded_year >= search_params.founded_after
                    )
                
                if search_params.founded_before is not None:
                    query = query.where(
                        self.model.founded_year <= search_params.founded_before
                    )
                
                # Tags filter
                if search_params.tags:
                    for tag in search_params.tags:
                        query = query.where(
                            self.model.tags.contains([tag])
                        )
                
                # Order by job count and rating
                query = query.order_by(
                    self.model.job_count.desc(),
                    self.model.glassdoor_rating.desc().nulls_last(),
                    self.model.name
                )
                
                # Apply pagination
                query = query.offset(skip).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error searching companies: {e}")
                return []
    
    async def get_companies_by_industry(
        self,
        industry: str,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Company]:
        """Get companies by industry."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    func.lower(self.model.industry).contains(industry.lower())
                )
                
                if active_only:
                    query = query.where(self.model.is_active == True)
                
                query = query.order_by(
                    self.model.job_count.desc(),
                    self.model.glassdoor_rating.desc().nulls_last()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting companies by industry: {e}")
                return []
    
    async def get_hiring_companies(self, limit: int = 100) -> List[Company]:
        """Get companies that are currently hiring."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.is_active == True,
                        self.model.is_hiring == True,
                        self.model.job_count > 0
                    )
                ).order_by(
                    self.model.job_count.desc(),
                    self.model.glassdoor_rating.desc().nulls_last()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting hiring companies: {e}")
                return []
    
    async def get_top_rated_companies(
        self,
        min_rating: float = 4.0,
        limit: int = 50
    ) -> List[Company]:
        """Get top-rated companies."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.is_active == True,
                        self.model.glassdoor_rating >= min_rating
                    )
                ).order_by(
                    self.model.glassdoor_rating.desc(),
                    self.model.job_count.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting top rated companies: {e}")
                return []
    
    async def get_startups(
        self,
        founded_after: int = 2014,  # Last 10 years
        limit: int = 50
    ) -> List[Company]:
        """Get startup companies."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(
                    and_(
                        self.model.is_active == True,
                        or_(
                            self.model.size == "startup",
                            self.model.founded_year >= founded_after
                        )
                    )
                ).order_by(
                    self.model.founded_year.desc().nulls_last(),
                    self.model.job_count.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting startups: {e}")
                return []
    
    async def get_companies_by_location(
        self,
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 100
    ) -> List[Company]:
        """Get companies by location."""
        async with self.get_session() as session:
            try:
                query = select(self.model).where(self.model.is_active == True)
                
                if country:
                    query = query.where(
                        func.lower(self.model.headquarters_country) == country.lower()
                    )
                
                if state:
                    query = query.where(
                        func.lower(self.model.headquarters_state) == state.lower()
                    )
                
                if city:
                    query = query.where(
                        func.lower(self.model.headquarters_city) == city.lower()
                    )
                
                query = query.order_by(
                    self.model.job_count.desc(),
                    self.model.glassdoor_rating.desc().nulls_last()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting companies by location: {e}")
                return []
    
    async def get_company_with_jobs(self, company_id: int) -> Optional[Company]:
        """Get company with associated jobs loaded."""
        async with self.get_session() as session:
            try:
                query = select(self.model).options(
                    selectinload(self.model.jobs)
                ).where(self.model.id == company_id)
                
                result = await session.execute(query)
                return result.scalar_one_or_none()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting company with jobs: {e}")
                return None
    
    async def update_job_count(self, company_id: int) -> Optional[Company]:
        """Update job count for a company."""
        async with self.get_session() as session:
            try:
                # Get current active job count
                from app.models.job import Job
                job_count_query = select(func.count(Job.id)).where(
                    and_(
                        Job.company_name == select(self.model.name).where(
                            self.model.id == company_id
                        ).scalar_subquery(),
                        Job.is_active == True
                    )
                )
                
                job_count_result = await session.execute(job_count_query)
                job_count = job_count_result.scalar() or 0
                
                # Update company
                company = await session.get(self.model, company_id)
                if company:
                    company.job_count = job_count
                    company.is_hiring = job_count > 0
                    await session.commit()
                    await session.refresh(company)
                    return company
                
                return None
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error updating job count for company {company_id}: {e}")
                return None
    
    async def get_company_statistics(self) -> Dict[str, Any]:
        """Get company statistics and analytics."""
        async with self.get_session() as session:
            try:
                # Total companies
                total_companies = await session.execute(
                    select(func.count(self.model.id))
                )
                total_count = total_companies.scalar() or 0
                
                # Active companies
                active_companies = await session.execute(
                    select(func.count(self.model.id)).where(
                        self.model.is_active == True
                    )
                )
                active_count = active_companies.scalar() or 0
                
                # Hiring companies
                hiring_companies = await session.execute(
                    select(func.count(self.model.id)).where(
                        and_(
                            self.model.is_active == True,
                            self.model.is_hiring == True
                        )
                    )
                )
                hiring_count = hiring_companies.scalar() or 0
                
                # Companies with good ratings
                rated_companies = await session.execute(
                    select(func.count(self.model.id)).where(
                        and_(
                            self.model.is_active == True,
                            self.model.glassdoor_rating >= 4.0
                        )
                    )
                )
                rated_count = rated_companies.scalar() or 0
                
                # Top industries by company count
                top_industries = await session.execute(
                    select(
                        self.model.industry,
                        func.count(self.model.id).label('company_count')
                    ).where(
                        and_(
                            self.model.is_active == True,
                            self.model.industry.isnot(None)
                        )
                    ).group_by(
                        self.model.industry
                    ).order_by(
                        func.count(self.model.id).desc()
                    ).limit(10)
                )
                
                # Top locations by company count
                top_locations = await session.execute(
                    select(
                        self.model.headquarters_country,
                        func.count(self.model.id).label('company_count')
                    ).where(
                        and_(
                            self.model.is_active == True,
                            self.model.headquarters_country.isnot(None)
                        )
                    ).group_by(
                        self.model.headquarters_country
                    ).order_by(
                        func.count(self.model.id).desc()
                    ).limit(10)
                )
                
                # Company size distribution
                size_distribution = await session.execute(
                    select(
                        self.model.size,
                        func.count(self.model.id).label('company_count')
                    ).where(
                        and_(
                            self.model.is_active == True,
                            self.model.size.isnot(None)
                        )
                    ).group_by(
                        self.model.size
                    ).order_by(
                        func.count(self.model.id).desc()
                    )
                )
                
                return {
                    "total_companies": total_count,
                    "active_companies": active_count,
                    "hiring_companies": hiring_count,
                    "well_rated_companies": rated_count,
                    "top_industries": [
                        {"industry": row.industry, "company_count": row.company_count}
                        for row in top_industries.all()
                    ],
                    "top_locations": [
                        {"country": row.headquarters_country, "company_count": row.company_count}
                        for row in top_locations.all()
                    ],
                    "size_distribution": [
                        {"size": row.size, "company_count": row.company_count}
                        for row in size_distribution.all()
                    ]
                }
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting company statistics: {e}")
                return {}
    
    async def find_similar_companies(
        self,
        company_id: int,
        limit: int = 10
    ) -> List[Company]:
        """Find companies similar to the given company."""
        async with self.get_session() as session:
            try:
                # Get the target company
                target_company = await session.get(self.model, company_id)
                if not target_company:
                    return []
                
                query = select(self.model).where(
                    and_(
                        self.model.id != company_id,
                        self.model.is_active == True
                    )
                )
                
                # Filter by same industry if available
                if target_company.industry:
                    query = query.where(self.model.industry == target_company.industry)
                
                # Filter by similar size if available
                if target_company.size:
                    query = query.where(self.model.size == target_company.size)
                
                # Order by similarity factors
                query = query.order_by(
                    self.model.glassdoor_rating.desc().nulls_last(),
                    self.model.job_count.desc()
                ).limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error finding similar companies: {e}")
                return []
    
    async def get_or_create_company(self, name: str, **kwargs) -> Company:
        """Get existing company or create new one."""
        async with self.get_session() as session:
            try:
                # Try to find existing company
                existing = await self.get_by_name(name)
                if existing:
                    return existing
                
                # Create new company
                company_data = {"name": name, **kwargs}
                company = self.model(**company_data)
                session.add(company)
                await session.commit()
                await session.refresh(company)
                return company
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error getting or creating company: {e}")
                raise
    
    async def bulk_update_job_counts(self) -> int:
        """Update job counts for all companies."""
        async with self.get_session() as session:
            try:
                # Update job counts using a single query
                result = await session.execute(
                    text("""
                        UPDATE companies 
                        SET job_count = (
                            SELECT COUNT(*) 
                            FROM jobs 
                            WHERE jobs.company_name = companies.name 
                            AND jobs.is_active = true
                        ),
                        is_hiring = (
                            SELECT COUNT(*) > 0
                            FROM jobs 
                            WHERE jobs.company_name = companies.name 
                            AND jobs.is_active = true
                        ),
                        updated_at = CURRENT_TIMESTAMP
                        WHERE companies.is_active = true
                    """)
                )
                
                await session.commit()
                return result.rowcount
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error bulk updating job counts: {e}")
                return 0