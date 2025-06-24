"""
Job Service Layer

Business logic for job management including creation, search, analysis,
and intelligent matching with comprehensive validation and caching.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.repositories.job_repository import JobRepository
from app.repositories.company_repository import CompanyRepository
from app.core.events import EventManager, event_manager
from app.core.database import CacheManager
from app.schemas.job import JobCreate, JobUpdate, JobSearchParams
from app.models.job import Job
from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobService:
    """Service layer for job operations."""
    
    def __init__(
        self,
        job_repo: JobRepository,
        company_repo: CompanyRepository,
        cache_manager: CacheManager,
        event_manager: EventManager,
        logger
    ):
        self.job_repo = job_repo
        self.company_repo = company_repo
        self.cache_manager = cache_manager
        self.event_manager = event_manager
        self.logger = logger
    
    async def search_jobs(
        self,
        search_params: JobSearchParams,
        skip: int = 0,
        limit: int = 100
    ) -> List[Job]:
        """
        Search jobs with advanced filtering and caching.
        
        Args:
            search_params: Search and filter parameters
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Job]: Matching jobs
        """
        try:
            # Generate cache key for search results
            cache_key = self._generate_search_cache_key(search_params, skip, limit)
            
            # Check cache first
            cached_results = await self.cache_manager.get(cache_key)
            if cached_results:
                self.logger.debug(f"Cache hit for job search: {cache_key}")
                # In production, you'd deserialize the cached results
                # For now, proceed with database query
            
            # Search in database
            jobs = await self.job_repo.search_jobs(search_params, skip, limit)
            
            # Cache results for 5 minutes
            await self._cache_search_results(cache_key, jobs)
            
            self.logger.info(f"Found {len(jobs)} jobs matching search criteria")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error searching jobs: {e}")
            raise
    
    async def get_job_by_id(self, job_id: int) -> Optional[Job]:
        """
        Get job by ID with caching.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Optional[Job]: Job if found
        """
        try:
            # Check cache first
            cache_key = f"job:{job_id}"
            cached_job = await self.cache_manager.get(cache_key)
            if cached_job:
                self.logger.debug(f"Cache hit for job {job_id}")
                # In production, deserialize cached job
            
            # Get from database
            job = await self.job_repo.get_by_id(job_id)
            
            if job:
                # Cache for 10 minutes
                await self.cache_manager.set(
                    cache_key,
                    "cached_job_data",  # In production, serialize job
                    expire_seconds=600
                )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error getting job {job_id}: {e}")
            raise
    
    async def create_job(
        self,
        job_data: JobCreate,
        created_by: Optional[str] = None
    ) -> Job:
        """
        Create new job with validation and duplicate detection.
        
        Args:
            job_data: Job creation data
            created_by: User who created the job
            
        Returns:
            Job: Created job
            
        Raises:
            ValueError: If validation fails or duplicate detected
        """
        try:
            # Validate job data
            await self._validate_job_data(job_data)
            
            # Check for duplicates
            if await self._is_duplicate_job(job_data):
                raise ValueError("Similar job already exists")
            
            # Create or get company
            company = None
            if job_data.company_name:
                company = await self.company_repo.get_or_create_company(
                    name=job_data.company_name,
                    website=getattr(job_data, 'company_website', None),
                    industry=getattr(job_data, 'industry', None)
                )
            
            # Create job
            job = await self.job_repo.create(job_data)
            
            if not job:
                raise ValueError("Failed to create job")
            
            # Update company job count
            if company:
                await self.company_repo.update_job_count(company.id)
            
            # Emit job created event
            await event_manager.emit("job_created", {
                "id": job.id,
                "title": job.title,
                "company_name": job.company_name,
                "created_by": created_by
            })
            
            # Invalidate relevant caches
            await self._invalidate_job_caches()
            
            self.logger.info(f"Job {job.id} created successfully")
            return job
            
        except Exception as e:
            self.logger.error(f"Error creating job: {e}")
            raise
    
    async def update_job(
        self,
        job_id: int,
        job_data: JobUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Job]:
        """
        Update existing job with validation.
        
        Args:
            job_id: Job identifier
            job_data: Update data
            updated_by: User who updated the job
            
        Returns:
            Optional[Job]: Updated job if successful
        """
        try:
            # Get existing job
            existing_job = await self.job_repo.get_by_id(job_id)
            if not existing_job:
                return None
            
            # Validate update data
            await self._validate_job_update(job_data, existing_job)
            
            # Update job
            updated_job = await self.job_repo.update(job_id, job_data)
            
            if updated_job:
                # Emit job updated event
                await self.event_manager.emit("job.updated", {
                    "id": job_id,
                    "updated_by": updated_by,
                    "changes": job_data.model_dump(exclude_unset=True)
                })
                
                # Invalidate caches
                await self._invalidate_job_cache(job_id)
                await self._invalidate_job_caches()
                
                self.logger.info(f"Job {job_id} updated successfully")
            
            return updated_job
            
        except Exception as e:
            self.logger.error(f"Error updating job {job_id}: {e}")
            raise
    
    async def delete_job(
        self,
        job_id: int,
        deleted_by: Optional[str] = None
    ) -> bool:
        """
        Delete job (soft delete).
        
        Args:
            job_id: Job identifier
            deleted_by: User who deleted the job
            
        Returns:
            bool: True if successful
        """
        try:
            # Get existing job
            existing_job = await self.job_repo.get_by_id(job_id)
            if not existing_job:
                return False
            
            # Soft delete (mark as inactive)
            success = await self.job_repo.update(job_id, JobUpdate(is_active=False))
            
            if success:
                # Emit job deleted event
                await self.event_manager.emit("job.deleted", {
                    "id": job_id,
                    "deleted_by": deleted_by
                })
                
                # Invalidate caches
                await self._invalidate_job_cache(job_id)
                await self._invalidate_job_caches()
                
                self.logger.info(f"Job {job_id} deleted successfully")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting job {job_id}: {e}")
            raise
    
    async def get_recent_jobs(
        self,
        days: int = 7,
        limit: int = 100
    ) -> List[Job]:
        """
        Get recently posted jobs.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of jobs
            
        Returns:
            List[Job]: Recent jobs
        """
        try:
            jobs = await self.job_repo.get_recent_jobs(days=days, limit=limit)
            self.logger.info(f"Retrieved {len(jobs)} recent jobs")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error getting recent jobs: {e}")
            raise
    
    async def get_high_scoring_jobs(
        self,
        user_id: Optional[str] = None,
        min_score: float = 0.8,
        limit: int = 50
    ) -> List[Job]:
        """
        Get jobs with high AI match scores.
        
        Args:
            user_id: User identifier for personalized results
            min_score: Minimum match score
            limit: Maximum number of jobs
            
        Returns:
            List[Job]: High-scoring jobs
        """
        try:
            jobs = await self.job_repo.get_high_scoring_jobs(
                min_score=int(min_score * 100),  # Convert to 0-100 scale
                limit=limit
            )
            
            self.logger.info(f"Retrieved {len(jobs)} high-scoring jobs")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error getting high-scoring jobs: {e}")
            raise
    
    async def count_jobs(self, search_params: JobSearchParams) -> int:
        """
        Count jobs matching search criteria.
        
        Args:
            search_params: Search parameters
            
        Returns:
            int: Number of matching jobs
        """
        try:
            # For now, use a simple approach
            # In production, implement efficient counting in repository
            filters = self._build_search_filters(search_params)
            count = await self.job_repo.count(filters)
            return count
            
        except Exception as e:
            self.logger.error(f"Error counting jobs: {e}")
            return 0
    
    async def get_job_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive job statistics.
        
        Returns:
            Dict[str, Any]: Job statistics
        """
        try:
            stats = await self.job_repo.get_job_statistics()
            
            # Add additional computed statistics
            stats["trends"] = await self._calculate_job_trends()
            stats["last_updated"] = datetime.utcnow().isoformat()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting job statistics: {e}")
            return {}
    
    async def schedule_analysis(self, job_id: int) -> None:
        """
        Schedule AI analysis for a job.
        
        Args:
            job_id: Job identifier
        """
        try:
            await self.event_manager.emit("analysis.requested", {
                "job_id": job_id,
                "analysis_type": "job_match",
                "priority": 3
            })
            
            self.logger.info(f"Analysis scheduled for job {job_id}")
            
        except Exception as e:
            self.logger.error(f"Error scheduling analysis for job {job_id}: {e}")
    
    # Private helper methods
    
    def _generate_search_cache_key(
        self,
        search_params: JobSearchParams,
        skip: int,
        limit: int
    ) -> str:
        """Generate cache key for search results."""
        import hashlib
        
        # Create a string representation of search parameters
        params = {
            **search_params.model_dump(),
            "skip": skip,
            "limit": limit
        }
        
        # Sort and stringify parameters
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
        
        # Hash to create shorter key
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        
        return f"job_search:{param_hash}"
    
    async def _cache_search_results(self, cache_key: str, jobs: List[Job]) -> None:
        """Cache search results."""
        try:
            # In production, properly serialize jobs
            await self.cache_manager.set(
                cache_key,
                f"cached_results_{len(jobs)}",  # Placeholder
                expire_seconds=300  # 5 minutes
            )
        except Exception as e:
            self.logger.error(f"Error caching search results: {e}")
    
    async def _validate_job_data(self, job_data: JobCreate) -> None:
        """Validate job creation data."""
        if not job_data.title or len(job_data.title.strip()) < 2:
            raise ValueError("Job title must be at least 2 characters")
        
        if not job_data.company_name or len(job_data.company_name.strip()) < 2:
            raise ValueError("Company name must be at least 2 characters")
        
        if job_data.salary_min and job_data.salary_max:
            if job_data.salary_min > job_data.salary_max:
                raise ValueError("Minimum salary cannot exceed maximum salary")
    
    async def _validate_job_update(self, job_data: JobUpdate, existing_job: Job) -> None:
        """Validate job update data."""
        if job_data.title and len(job_data.title.strip()) < 2:
            raise ValueError("Job title must be at least 2 characters")
        
        if job_data.salary_min and job_data.salary_max:
            if job_data.salary_min > job_data.salary_max:
                raise ValueError("Minimum salary cannot exceed maximum salary")
    
    async def _is_duplicate_job(self, job_data: JobCreate) -> bool:
        """Check if job is a duplicate."""
        try:
            return await self.job_repo.duplicate_check(
                title=job_data.title,
                company_name=job_data.company_name,
                source_url=getattr(job_data, 'source_url', f"manual_{datetime.utcnow().timestamp()}")
            )
        except Exception as e:
            self.logger.error(f"Error checking duplicates: {e}")
            return False
    
    def _build_search_filters(self, search_params: JobSearchParams) -> Dict[str, Any]:
        """Build filters for database queries."""
        filters = {}
        
        if search_params.location:
            filters["location"] = search_params.location
        
        if search_params.company:
            filters["company_name"] = search_params.company
        
        if search_params.job_type:
            filters["employment_type"] = search_params.job_type
        
        if search_params.is_remote is not None:
            filters["remote_friendly"] = search_params.is_remote
        
        return filters
    
    async def _calculate_job_trends(self) -> Dict[str, Any]:
        """Calculate job market trends."""
        try:
            # Get jobs from last 30 days
            recent_jobs = await self.job_repo.get_recent_jobs(days=30, limit=1000)
            
            # Calculate basic trends
            trends = {
                "total_recent": len(recent_jobs),
                "remote_percentage": 0,
                "top_companies": {},
                "top_locations": {}
            }
            
            if recent_jobs:
                # Calculate remote job percentage
                remote_count = sum(1 for job in recent_jobs if job.remote_friendly)
                trends["remote_percentage"] = (remote_count / len(recent_jobs)) * 100
                
                # Count top companies
                company_counts = {}
                location_counts = {}
                
                for job in recent_jobs:
                    if job.company_name:
                        company_counts[job.company_name] = company_counts.get(job.company_name, 0) + 1
                    
                    if job.location:
                        location_counts[job.location] = location_counts.get(job.location, 0) + 1
                
                # Get top 5
                trends["top_companies"] = dict(
                    sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                )
                trends["top_locations"] = dict(
                    sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                )
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error calculating trends: {e}")
            return {}
    
    async def _invalidate_job_cache(self, job_id: int) -> None:
        """Invalidate cache for specific job."""
        try:
            await self.cache_manager.delete(f"job:{job_id}")
        except Exception as e:
            self.logger.error(f"Error invalidating job cache: {e}")
    
    async def _invalidate_job_caches(self) -> None:
        """Invalidate general job caches."""
        try:
            # In production, use pattern-based cache invalidation
            # For now, just log
            self.logger.debug("Invalidating job search caches")
        except Exception as e:
            self.logger.error(f"Error invalidating caches: {e}")