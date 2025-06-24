"""
Analysis Service Layer

Business logic for AI-powered job analysis, matching algorithms,
market insights, and personalized recommendations.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import asyncio
import json

from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.job_repository import JobRepository
from app.core.events import EventManager
from app.core.database import CacheManager
from app.core.config import get_settings
from app.schemas.analysis import AnalysisCreate, AnalysisUpdate
from app.models.analysis import Analysis
from app.models.job import Job
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AnalysisService:
    """Service layer for AI analysis operations."""
    
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        job_repo: JobRepository,
        cache_manager: CacheManager,
        event_manager: EventManager,
        settings,
        logger
    ):
        self.analysis_repo = analysis_repo
        self.job_repo = job_repo
        self.cache_manager = cache_manager
        self.event_manager = event_manager
        self.settings = settings
        self.logger = logger
    
    async def analyze_job_match(
        self,
        job_id: int,
        user_id: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze job match for a specific user.
        
        Args:
            job_id: Job identifier
            user_id: User identifier
            force_refresh: Force new analysis even if cached
            
        Returns:
            Optional[Dict[str, Any]]: Analysis results
        """
        try:
            # Check for existing analysis
            if not force_refresh:
                existing_analysis = await self.analysis_repo.get_latest_analysis(
                    job_id=job_id,
                    analysis_type="job_match",
                    user_id=user_id
                )
                
                if existing_analysis and existing_analysis.is_recent:
                    self.logger.info(f"Using existing analysis for job {job_id} and user {user_id}")
                    return self._format_job_match_response(existing_analysis)
            
            # Get job details
            job = await self.job_repo.get_by_id(job_id)
            if not job:
                return None
            
            # Get user profile
            user_profile = await self._get_user_profile(user_id)
            
            # Perform AI analysis
            analysis_results = await self._perform_job_analysis(job, user_profile)
            
            # Save analysis to database
            analysis_data = AnalysisCreate(
                job_id=job_id,
                analysis_type="job_match",
                results=analysis_results,
                confidence_score=analysis_results.get("confidence_score", 0.0)
            )
            
            analysis = await self.analysis_repo.create(analysis_data)
            if analysis:
                # Update with detailed scores
                await self.analysis_repo.update(analysis.id, AnalysisUpdate(
                    match_score=analysis_results.get("overall_match_score"),
                    skill_match_score=analysis_results.get("skill_match_score"),
                    experience_match_score=analysis_results.get("experience_match_score"),
                    location_match_score=analysis_results.get("location_match_score"),
                    salary_match_score=analysis_results.get("salary_match_score"),
                    key_insights=analysis_results.get("key_insights"),
                    recommendations=analysis_results.get("recommendations")
                ))
            
            # Emit analysis completed event
            await self.event_manager.emit("analysis.completed", {
                "job_id": job_id,
                "user_id": user_id,
                "analysis_id": analysis.id if analysis else None,
                "match_score": analysis_results.get("overall_match_score")
            })
            
            self.logger.info(f"Job match analysis completed for job {job_id} and user {user_id}")
            return self._format_job_match_response(analysis, analysis_results)
            
        except Exception as e:
            self.logger.error(f"Error analyzing job match: {e}")
            return None
    
    async def create_analysis(
        self,
        analysis_data: AnalysisCreate,
        user_id: str
    ) -> Analysis:
        """
        Create new analysis request.
        
        Args:
            analysis_data: Analysis creation data
            user_id: User identifier
            
        Returns:
            Analysis: Created analysis
        """
        try:
            # Add user ID to analysis data
            analysis_data.user_id = user_id
            
            # Create analysis in pending state
            analysis = await self.analysis_repo.create(analysis_data)
            
            if analysis:
                # Emit analysis started event
                await self.event_manager.emit("analysis.started", {
                    "analysis_id": analysis.id,
                    "user_id": user_id,
                    "analysis_type": analysis.analysis_type
                })
                
                self.logger.info(f"Analysis {analysis.id} created for user {user_id}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error creating analysis: {e}")
            raise
    
    async def process_analysis(self, analysis_id: int) -> None:
        """
        Process analysis in background.
        
        Args:
            analysis_id: Analysis identifier
        """
        try:
            # Get analysis
            analysis = await self.analysis_repo.get_by_id(analysis_id)
            if not analysis:
                return
            
            # Update status to processing
            await self.analysis_repo.update_analysis_status(
                analysis_id,
                "processing"
            )
            
            # Process based on analysis type
            if analysis.analysis_type == "job_match":
                await self._process_job_match_analysis(analysis)
            elif analysis.analysis_type == "market_analysis":
                await self._process_market_analysis(analysis)
            elif analysis.analysis_type == "skill_gap":
                await self._process_skill_gap_analysis(analysis)
            
            self.logger.info(f"Analysis {analysis_id} processed successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing analysis {analysis_id}: {e}")
            # Mark as failed
            await self.analysis_repo.update_analysis_status(
                analysis_id,
                "failed",
                error_message=str(e)
            )
    
    async def search_analyses(
        self,
        user_id: str,
        analysis_type: Optional[str] = None,
        min_match_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Analysis]:
        """
        Search user's analyses with filtering.
        
        Args:
            user_id: User identifier
            analysis_type: Filter by analysis type
            min_match_score: Minimum match score
            min_confidence: Minimum confidence score
            status: Filter by status
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List[Analysis]: Matching analyses
        """
        try:
            analyses = await self.analysis_repo.search_analyses(
                user_id=user_id,
                analysis_type=analysis_type,
                min_match_score=min_match_score,
                min_confidence=min_confidence,
                status=status,
                skip=skip,
                limit=limit
            )
            
            self.logger.info(f"Found {len(analyses)} analyses for user {user_id}")
            return analyses
            
        except Exception as e:
            self.logger.error(f"Error searching analyses: {e}")
            return []
    
    async def get_analysis_by_id(
        self,
        analysis_id: int,
        user_id: str
    ) -> Optional[Analysis]:
        """
        Get analysis by ID with user validation.
        
        Args:
            analysis_id: Analysis identifier
            user_id: User identifier
            
        Returns:
            Optional[Analysis]: Analysis if found and authorized
        """
        try:
            analysis = await self.analysis_repo.get_by_id(analysis_id)
            
            # Verify user owns this analysis
            if analysis and analysis.user_id == user_id:
                return analysis
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting analysis {analysis_id}: {e}")
            return None
    
    async def count_analyses(
        self,
        user_id: str,
        analysis_type: Optional[str] = None,
        min_match_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Count user's analyses matching criteria.
        
        Args:
            user_id: User identifier
            analysis_type: Filter by analysis type
            min_match_score: Minimum match score
            min_confidence: Minimum confidence score
            status: Filter by status
            
        Returns:
            int: Number of matching analyses
        """
        try:
            # Use search with large limit to count
            # In production, implement efficient counting
            analyses = await self.search_analyses(
                user_id=user_id,
                analysis_type=analysis_type,
                min_match_score=min_match_score,
                min_confidence=min_confidence,
                status=status,
                limit=10000
            )
            return len(analyses)
            
        except Exception as e:
            self.logger.error(f"Error counting analyses: {e}")
            return 0
    
    async def delete_analysis(
        self,
        analysis_id: int,
        user_id: str
    ) -> bool:
        """
        Delete analysis with user validation.
        
        Args:
            analysis_id: Analysis identifier
            user_id: User identifier
            
        Returns:
            bool: True if successful
        """
        try:
            # Verify ownership
            analysis = await self.get_analysis_by_id(analysis_id, user_id)
            if not analysis:
                return False
            
            success = await self.analysis_repo.delete(analysis_id)
            
            if success:
                self.logger.info(f"Analysis {analysis_id} deleted by user {user_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting analysis {analysis_id}: {e}")
            return False
    
    async def generate_market_insights(
        self,
        location: Optional[str] = None,
        job_type: Optional[str] = None,
        industry: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Generate market insights and trends.
        
        Args:
            location: Location filter
            job_type: Job type filter
            industry: Industry filter
            days_back: Days to analyze
            
        Returns:
            Dict[str, Any]: Market insights
        """
        try:
            # Generate cache key
            cache_key = f"market_insights:{location}:{job_type}:{industry}:{days_back}"
            
            # Check cache
            cached_insights = await self.cache_manager.get(cache_key)
            if cached_insights:
                return json.loads(cached_insights)
            
            # Get jobs for analysis
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            recent_jobs = await self.job_repo.get_recent_jobs(days=days_back, limit=1000)
            
            # Apply filters
            filtered_jobs = self._filter_jobs_for_insights(
                recent_jobs, location, job_type, industry
            )
            
            # Generate insights
            insights = await self._generate_insights_from_jobs(filtered_jobs, days_back)
            
            # Cache for 1 hour
            await self.cache_manager.set(
                cache_key,
                json.dumps(insights, default=str),
                expire_seconds=3600
            )
            
            self.logger.info(f"Generated market insights for {len(filtered_jobs)} jobs")
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating market insights: {e}")
            return {}
    
    async def analyze_skill_gap(
        self,
        user_id: str,
        target_role: str,
        user_skills: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze skill gaps for target role.
        
        Args:
            user_id: User identifier
            target_role: Target job role
            user_skills: User's current skills
            
        Returns:
            Dict[str, Any]: Skill gap analysis
        """
        try:
            # Get jobs matching target role
            from app.schemas.job import JobSearchParams
            search_params = JobSearchParams(query=target_role)
            target_jobs = await self.job_repo.search_jobs(search_params, limit=100)
            
            # Extract required skills from job descriptions
            required_skills = await self._extract_skills_from_jobs(target_jobs)
            
            # Analyze skill gaps
            skill_analysis = await self._analyze_skill_gaps(
                user_skills, required_skills, target_role
            )
            
            self.logger.info(f"Skill gap analysis completed for user {user_id}")
            return skill_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing skill gap: {e}")
            return {}
    
    async def get_analysis_statistics(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get analysis statistics.
        
        Args:
            user_id: User identifier (optional for global stats)
            
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            stats = await self.analysis_repo.get_analysis_statistics(user_id)
            
            # Add additional metrics
            if user_id:
                stats["recent_high_matches"] = len(
                    await self.analysis_repo.get_high_match_analyses(
                        user_id=user_id,
                        min_score=0.8,
                        limit=50
                    )
                )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting analysis statistics: {e}")
            return {}
    
    # Private helper methods
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile for analysis."""
        # In production, fetch from user service or database
        # For now, return mock data
        return {
            "skills": ["Python", "Data Analysis", "SQL", "Machine Learning"],
            "experience_level": "mid",
            "preferred_locations": ["Remote", "San Francisco"],
            "salary_expectations": {"min": 80000, "max": 120000},
            "education": "Masters",
            "industry_preferences": ["Technology", "Finance"]
        }
    
    async def _perform_job_analysis(
        self,
        job: Job,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform AI-powered job analysis."""
        try:
            # Simulate AI analysis with comprehensive scoring
            analysis_results = {
                "overall_match_score": 0.0,
                "confidence_score": 0.85,
                "skill_match_score": 0.0,
                "experience_match_score": 0.0,
                "location_match_score": 0.0,
                "salary_match_score": 0.0,
                "culture_match_score": 0.0,
                "key_insights": {},
                "recommendations": {},
                "red_flags": {}
            }
            
            # Skill matching
            job_skills = self._extract_skills_from_description(
                job.description or "",
                job.requirements or ""
            )
            user_skills = user_profile.get("skills", [])
            skill_score = self._calculate_skill_match(job_skills, user_skills)
            analysis_results["skill_match_score"] = skill_score
            
            # Experience matching
            experience_score = self._calculate_experience_match(
                job, user_profile.get("experience_level", "entry")
            )
            analysis_results["experience_match_score"] = experience_score
            
            # Location matching
            location_score = self._calculate_location_match(
                job.location, user_profile.get("preferred_locations", [])
            )
            analysis_results["location_match_score"] = location_score
            
            # Salary matching
            salary_score = self._calculate_salary_match(
                job, user_profile.get("salary_expectations", {})
            )
            analysis_results["salary_match_score"] = salary_score
            
            # Culture matching (basic implementation)
            culture_score = 0.75  # Placeholder
            analysis_results["culture_match_score"] = culture_score
            
            # Calculate overall score
            weights = {
                "skill": 0.4,
                "experience": 0.2,
                "location": 0.15,
                "salary": 0.15,
                "culture": 0.1
            }
            
            overall_score = (
                skill_score * weights["skill"] +
                experience_score * weights["experience"] +
                location_score * weights["location"] +
                salary_score * weights["salary"] +
                culture_score * weights["culture"]
            )
            analysis_results["overall_match_score"] = overall_score
            
            # Generate insights
            analysis_results["key_insights"] = self._generate_insights(
                job, user_profile, analysis_results
            )
            
            # Generate recommendations
            analysis_results["recommendations"] = self._generate_recommendations(
                job, user_profile, analysis_results
            )
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error performing job analysis: {e}")
            return {
                "overall_match_score": 0.0,
                "confidence_score": 0.0,
                "error": str(e)
            }
    
    def _extract_skills_from_description(
        self,
        description: str,
        requirements: str
    ) -> List[str]:
        """Extract skills from job description."""
        # Simple keyword-based extraction
        # In production, use NLP models
        skill_keywords = [
            "python", "java", "javascript", "sql", "react", "node.js",
            "machine learning", "data analysis", "aws", "docker",
            "kubernetes", "git", "agile", "scrum", "project management"
        ]
        
        text = (description + " " + requirements).lower()
        found_skills = [skill for skill in skill_keywords if skill in text]
        
        return found_skills
    
    def _calculate_skill_match(
        self,
        job_skills: List[str],
        user_skills: List[str]
    ) -> float:
        """Calculate skill match score."""
        if not job_skills:
            return 0.8  # Default score if no skills specified
        
        user_skills_lower = [skill.lower() for skill in user_skills]
        job_skills_lower = [skill.lower() for skill in job_skills]
        
        matches = sum(1 for skill in job_skills_lower if skill in user_skills_lower)
        score = matches / len(job_skills_lower) if job_skills_lower else 0.0
        
        return min(score, 1.0)
    
    def _calculate_experience_match(
        self,
        job: Job,
        user_experience: str
    ) -> float:
        """Calculate experience level match."""
        experience_levels = {
            "entry": 1,
            "junior": 2,
            "mid": 3,
            "senior": 4,
            "lead": 5,
            "principal": 6
        }
        
        user_level = experience_levels.get(user_experience.lower(), 3)
        
        # Try to extract experience level from job
        job_text = (job.title + " " + (job.description or "")).lower()
        job_level = 3  # Default to mid-level
        
        if "entry" in job_text or "junior" in job_text:
            job_level = 2
        elif "senior" in job_text:
            job_level = 4
        elif "lead" in job_text or "principal" in job_text:
            job_level = 5
        
        # Calculate match (closer levels = higher score)
        level_diff = abs(user_level - job_level)
        score = max(0.0, 1.0 - (level_diff * 0.2))
        
        return score
    
    def _calculate_location_match(
        self,
        job_location: Optional[str],
        user_preferences: List[str]
    ) -> float:
        """Calculate location match score."""
        if not job_location:
            return 0.5  # Neutral score if no location specified
        
        if not user_preferences:
            return 0.7  # Default score if user has no preferences
        
        job_location_lower = job_location.lower()
        user_prefs_lower = [pref.lower() for pref in user_preferences]
        
        # Check for exact matches or "remote"
        for pref in user_prefs_lower:
            if pref in job_location_lower or job_location_lower in pref:
                return 1.0
            if "remote" in pref and ("remote" in job_location_lower or job.remote_friendly):
                return 1.0
        
        # Partial match for cities/states
        return 0.3
    
    def _calculate_salary_match(
        self,
        job: Job,
        user_expectations: Dict[str, int]
    ) -> float:
        """Calculate salary match score."""
        if not user_expectations:
            return 0.7  # Default if no expectations
        
        user_min = user_expectations.get("min", 0)
        user_max = user_expectations.get("max", float('inf'))
        
        # If job has no salary info, return neutral score
        if not job.salary_min and not job.salary_max:
            return 0.6
        
        job_min = job.salary_min or 0
        job_max = job.salary_max or job_min or user_max
        
        # Calculate overlap
        overlap_min = max(user_min, job_min)
        overlap_max = min(user_max, job_max)
        
        if overlap_min <= overlap_max:
            # There's overlap
            overlap_size = overlap_max - overlap_min
            user_range = user_max - user_min
            job_range = job_max - job_min
            
            if user_range > 0 and job_range > 0:
                score = overlap_size / max(user_range, job_range)
                return min(score, 1.0)
            else:
                return 0.8
        else:
            # No overlap - calculate distance penalty
            if user_max < job_min:
                # Job pays more than user expects
                return 0.9  # High score - good for user
            else:
                # Job pays less than user expects
                gap = user_min - job_max
                penalty = min(gap / user_min, 0.8) if user_min > 0 else 0.8
                return max(0.1, 1.0 - penalty)
    
    def _generate_insights(
        self,
        job: Job,
        user_profile: Dict[str, Any],
        scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate key insights from analysis."""
        insights = {
            "strengths": [],
            "concerns": [],
            "opportunities": []
        }
        
        # Analyze strengths
        if scores["skill_match_score"] > 0.8:
            insights["strengths"].append("Strong skill alignment with job requirements")
        
        if scores["experience_match_score"] > 0.8:
            insights["strengths"].append("Experience level matches job expectations")
        
        if scores["location_match_score"] > 0.9:
            insights["strengths"].append("Location preference perfectly aligned")
        
        # Analyze concerns
        if scores["skill_match_score"] < 0.5:
            insights["concerns"].append("Significant skill gap identified")
        
        if scores["salary_match_score"] < 0.4:
            insights["concerns"].append("Salary expectations may not align")
        
        # Analyze opportunities
        if 0.6 <= scores["overall_match_score"] <= 0.8:
            insights["opportunities"].append("Good match with room for growth")
        
        return insights
    
    def _generate_recommendations(
        self,
        job: Job,
        user_profile: Dict[str, Any],
        scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate personalized recommendations."""
        recommendations = {
            "apply": [],
            "improve": [],
            "research": []
        }
        
        overall_score = scores["overall_match_score"]
        
        if overall_score > 0.8:
            recommendations["apply"].append("Highly recommended - apply immediately")
            recommendations["apply"].append("Tailor resume to highlight matching skills")
        elif overall_score > 0.6:
            recommendations["apply"].append("Good candidate - consider applying")
            recommendations["improve"].append("Address skill gaps before applying")
        else:
            recommendations["improve"].append("Focus on developing required skills")
            recommendations["research"].append("Research company culture and values")
        
        return recommendations
    
    def _format_job_match_response(
        self,
        analysis: Optional[Analysis],
        results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format job match analysis response."""
        if not analysis and not results:
            return {}
        
        if results:
            # Use provided results
            response_data = results
        else:
            # Use analysis data
            response_data = analysis.results
        
        return {
            "job_id": analysis.job_id if analysis else None,
            "analysis_id": analysis.id if analysis else None,
            "overall_match_score": response_data.get("overall_match_score", 0.0),
            "confidence_score": response_data.get("confidence_score", 0.0),
            "skill_match_score": response_data.get("skill_match_score"),
            "experience_match_score": response_data.get("experience_match_score"),
            "location_match_score": response_data.get("location_match_score"),
            "salary_match_score": response_data.get("salary_match_score"),
            "culture_match_score": response_data.get("culture_match_score"),
            "match_level": self._get_match_level(response_data.get("overall_match_score", 0.0)),
            "match_reasons": self._get_match_reasons(response_data),
            "strengths": response_data.get("key_insights", {}).get("strengths", []),
            "concerns": response_data.get("key_insights", {}).get("concerns", []),
            "application_priority": self._get_application_priority(response_data.get("overall_match_score", 0.0)),
            "next_steps": response_data.get("recommendations", {}).get("apply", []),
            "created_at": analysis.created_at if analysis else datetime.utcnow()
        }
    
    def _get_match_level(self, score: float) -> str:
        """Get match level description."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "fair"
        else:
            return "poor"
    
    def _get_match_reasons(self, results: Dict[str, Any]) -> List[str]:
        """Get reasons for match score."""
        reasons = []
        
        if results.get("skill_match_score", 0) > 0.8:
            reasons.append("Strong skill alignment")
        
        if results.get("experience_match_score", 0) > 0.8:
            reasons.append("Experience level matches")
        
        if results.get("location_match_score", 0) > 0.8:
            reasons.append("Location preference aligned")
        
        if results.get("salary_match_score", 0) > 0.8:
            reasons.append("Salary expectations met")
        
        return reasons
    
    def _get_application_priority(self, score: float) -> str:
        """Get application priority level."""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        else:
            return "low"
    
    async def _process_job_match_analysis(self, analysis: Analysis) -> None:
        """Process job match analysis."""
        # Implementation would perform actual AI analysis
        # For now, mark as completed
        await self.analysis_repo.update_analysis_status(
            analysis.id,
            "completed"
        )
    
    async def _process_market_analysis(self, analysis: Analysis) -> None:
        """Process market analysis."""
        # Implementation would perform market analysis
        await self.analysis_repo.update_analysis_status(
            analysis.id,
            "completed"
        )
    
    async def _process_skill_gap_analysis(self, analysis: Analysis) -> None:
        """Process skill gap analysis."""
        # Implementation would perform skill gap analysis
        await self.analysis_repo.update_analysis_status(
            analysis.id,
            "completed"
        )