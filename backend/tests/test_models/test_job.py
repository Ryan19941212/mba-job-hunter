"""
Tests for Job model.

Tests database operations, model validations, properties,
and relationships for the Job model.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.job import Job


@pytest.mark.database
@pytest.mark.unit
class TestJobModel:
    """Test Job model functionality."""
    
    async def test_create_job(self, test_db, sample_job_data):
        """Test creating a job with valid data."""
        job = Job(
            title=sample_job_data["title"],
            company_name=sample_job_data["company_name"],
            location=sample_job_data["location"],
            description=sample_job_data["description"],
            requirements=sample_job_data["requirements"],
            salary_min=sample_job_data["salary_min"],
            salary_max=sample_job_data["salary_max"],
            currency=sample_job_data["salary_currency"],
            source_url=sample_job_data["source_url"],
            source_platform=sample_job_data["source_platform"]
        )
        
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        assert job.id is not None
        assert job.title == sample_job_data["title"]
        assert job.company_name == sample_job_data["company_name"]
        assert job.created_at is not None
        assert job.updated_at is not None
        assert job.is_active is True
    
    async def test_job_required_fields(self, test_db):
        """Test that required fields are enforced."""
        # Test missing title
        with pytest.raises(IntegrityError):
            job = Job(
                company_name="Test Company",
                source_url="https://example.com/job",
                source_platform="indeed"
            )
            test_db.add(job)
            await test_db.commit()
    
    async def test_job_unique_source_url(self, test_db, sample_job_data):
        """Test that source_url is unique."""
        # Create first job
        job1 = Job(
            title="Job 1",
            company_name="Company 1",
            source_url="https://example.com/job/123",
            source_platform="indeed"
        )
        test_db.add(job1)
        await test_db.commit()
        
        # Try to create second job with same URL
        with pytest.raises(IntegrityError):
            job2 = Job(
                title="Job 2",
                company_name="Company 2",
                source_url="https://example.com/job/123",
                source_platform="indeed"
            )
            test_db.add(job2)
            await test_db.commit()
    
    async def test_job_salary_range_validation(self, test_db):
        """Test salary range validation constraints."""
        # Test invalid AI fit score (> 100)
        with pytest.raises(IntegrityError):
            job = Job(
                title="Test Job",
                company_name="Test Company",
                source_url="https://example.com/job",
                source_platform="indeed",
                ai_fit_score=150  # Invalid: > 100
            )
            test_db.add(job)
            await test_db.commit()
        
        # Test invalid AI fit score (< 0)
        with pytest.raises(IntegrityError):
            job = Job(
                title="Test Job",
                company_name="Test Company",
                source_url="https://example.com/job2",
                source_platform="indeed",
                ai_fit_score=-10  # Invalid: < 0
            )
            test_db.add(job)
            await test_db.commit()
    
    async def test_job_employment_type_validation(self, test_db):
        """Test employment type validation."""
        # Valid employment type
        job = Job(
            title="Test Job",
            company_name="Test Company",
            source_url="https://example.com/job",
            source_platform="indeed",
            employment_type="Full-time"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        assert job.employment_type == "Full-time"
        
        # Invalid employment type should fail
        with pytest.raises(IntegrityError):
            job2 = Job(
                title="Test Job 2",
                company_name="Test Company 2",
                source_url="https://example.com/job2",
                source_platform="indeed",
                employment_type="Invalid Type"
            )
            test_db.add(job2)
            await test_db.commit()
    
    async def test_job_source_platform_validation(self, test_db):
        """Test source platform validation."""
        # Valid platform
        job = Job(
            title="Test Job",
            company_name="Test Company",
            source_url="https://example.com/job",
            source_platform="linkedin"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        assert job.source_platform == "linkedin"
        
        # Invalid platform should fail
        with pytest.raises(IntegrityError):
            job2 = Job(
                title="Test Job 2",
                company_name="Test Company 2",
                source_url="https://example.com/job2",
                source_platform="invalid_platform"
            )
            test_db.add(job2)
            await test_db.commit()
    
    async def test_job_properties(self, test_db, sample_job_data):
        """Test Job model properties."""
        # Create job with salary info
        job = Job(
            title=sample_job_data["title"],
            company_name=sample_job_data["company_name"],
            source_url=sample_job_data["source_url"],
            source_platform=sample_job_data["source_platform"],
            salary_min=sample_job_data["salary_min"],
            salary_max=sample_job_data["salary_max"],
            currency=sample_job_data["salary_currency"],
            posted_date=datetime.now(timezone.utc) - timedelta(days=15)
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # Test salary_range_display property
        expected_range = f"${job.salary_min:,} - ${job.salary_max:,}"
        assert job.salary_range_display == expected_range
        
        # Test has_salary_info property
        assert job.has_salary_info is True
        
        # Test is_recent property (job is 15 days old, should not be recent)
        assert job.is_recent is True  # Within 30 days
        
        # Test is_expired property (no expiration date)
        assert job.is_expired is False
    
    async def test_job_without_salary(self, test_db):
        """Test job properties without salary information."""
        job = Job(
            title="Test Job",
            company_name="Test Company",
            source_url="https://example.com/job",
            source_platform="indeed"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # Test properties when no salary info
        assert job.salary_range_display is None
        assert job.has_salary_info is False
    
    async def test_job_with_expiration(self, test_db):
        """Test job expiration functionality."""
        # Create expired job
        expired_job = Job(
            title="Expired Job",
            company_name="Test Company",
            source_url="https://example.com/expired",
            source_platform="indeed",
            expires_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        test_db.add(expired_job)
        
        # Create non-expired job
        active_job = Job(
            title="Active Job",
            company_name="Test Company",
            source_url="https://example.com/active",
            source_platform="indeed",
            expires_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        test_db.add(active_job)
        
        await test_db.commit()
        await test_db.refresh(expired_job)
        await test_db.refresh(active_job)
        
        assert expired_job.is_expired is True
        assert active_job.is_expired is False
    
    async def test_job_skills_array(self, test_db):
        """Test extracted_skills array field."""
        skills = ["Python", "SQL", "MBA", "Leadership", "Strategy"]
        
        job = Job(
            title="Test Job",
            company_name="Test Company",
            source_url="https://example.com/job",
            source_platform="indeed",
            extracted_skills=skills
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        assert job.extracted_skills == skills
        assert len(job.extracted_skills) == 5
        assert "MBA" in job.extracted_skills
    
    async def test_job_repr(self, test_db):
        """Test Job string representation."""
        job = Job(
            title="Test Job",
            company_name="Test Company",
            source_url="https://example.com/job",
            source_platform="indeed"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        repr_str = repr(job)
        assert "Test Job" in repr_str
        assert "Test Company" in repr_str
        assert str(job.id) in repr_str
    
    async def test_job_timestamps(self, test_db):
        """Test automatic timestamp handling."""
        job = Job(
            title="Test Job",
            company_name="Test Company",
            source_url="https://example.com/job",
            source_platform="indeed"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        created_time = job.created_at
        updated_time = job.updated_at
        
        assert created_time is not None
        assert updated_time is not None
        
        # Update the job
        job.title = "Updated Job Title"
        await test_db.commit()
        await test_db.refresh(job)
        
        # created_at should remain the same, updated_at should change
        assert job.created_at == created_time
        assert job.updated_at > updated_time
    
    async def test_query_jobs(self, test_db, sample_job_list):
        """Test querying jobs from database."""
        # Add multiple jobs
        jobs = []
        for job_data in sample_job_list:
            job = Job(
                title=job_data["title"],
                company_name=job_data["company_name"],
                source_url=job_data["source_url"],
                source_platform="indeed",
                salary_min=job_data["salary_min"],
                salary_max=job_data["salary_max"]
            )
            jobs.append(job)
            test_db.add(job)
        
        await test_db.commit()
        
        # Query all jobs
        result = await test_db.execute(select(Job))
        all_jobs = result.scalars().all()
        
        assert len(all_jobs) == len(sample_job_list)
        
        # Query jobs by company
        result = await test_db.execute(
            select(Job).where(Job.company_name == "Test Company 1")
        )
        company_jobs = result.scalars().all()
        
        assert len(company_jobs) == 1
        assert company_jobs[0].company_name == "Test Company 1"
        
        # Query jobs with salary range
        result = await test_db.execute(
            select(Job).where(Job.salary_min >= 100000)
        )
        high_salary_jobs = result.scalars().all()
        
        assert len(high_salary_jobs) > 0
        for job in high_salary_jobs:
            assert job.salary_min >= 100000
    
    async def test_job_indexes(self, test_db, sample_job_list):
        """Test that database indexes work correctly."""
        # Add jobs for index testing
        for job_data in sample_job_list:
            job = Job(
                title=job_data["title"],
                company_name=job_data["company_name"],
                location="San Francisco, CA",
                source_url=job_data["source_url"],
                source_platform="indeed",
                salary_min=job_data["salary_min"],
                posted_date=datetime.now(timezone.utc),
                is_active=True
            )
            test_db.add(job)
        
        await test_db.commit()
        
        # Test indexed queries (these should be efficient)
        queries = [
            select(Job).where(Job.title.contains("Job")),
            select(Job).where(Job.company_name == "Test Company 1"),
            select(Job).where(Job.location == "San Francisco, CA"),
            select(Job).where(Job.salary_min >= 90000),
            select(Job).where(Job.is_active == True),
            select(Job).where(Job.source_platform == "indeed")
        ]
        
        for query in queries:
            result = await test_db.execute(query)
            jobs = result.scalars().all()
            # Just verify the queries work - actual performance testing
            # would require a larger dataset
            assert isinstance(jobs, list)