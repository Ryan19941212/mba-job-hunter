"""
Tests for Jobs API endpoints.

Tests CRUD operations, search functionality, filtering,
and error handling for job-related API endpoints.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

from app.models.job import Job


@pytest.mark.api
@pytest.mark.asyncio
class TestJobsAPI:
    """Test Jobs API endpoints."""
    
    async def test_get_jobs_empty(self, test_client: AsyncClient):
        """Test getting jobs when database is empty."""
        response = await test_client.get("/api/v1/jobs/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []
        assert data["page"] == 1
        assert data["per_page"] == 20
    
    async def test_get_jobs_with_data(self, test_client: AsyncClient, sample_job_in_db):
        """Test getting jobs with data in database."""
        response = await test_client.get("/api/v1/jobs/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["jobs"]) == 1
        
        job = data["jobs"][0]
        assert job["title"] == sample_job_in_db.title
        assert job["company_name"] == sample_job_in_db.company_name
        assert job["id"] == sample_job_in_db.id
    
    async def test_get_job_by_id(self, test_client: AsyncClient, sample_job_in_db):
        """Test getting a specific job by ID."""
        response = await test_client.get(f"/api/v1/jobs/{sample_job_in_db.id}")
        
        assert response.status_code == 200
        job = response.json()
        assert job["id"] == sample_job_in_db.id
        assert job["title"] == sample_job_in_db.title
        assert job["company_name"] == sample_job_in_db.company_name
        assert job["description"] == sample_job_in_db.description
    
    async def test_get_job_not_found(self, test_client: AsyncClient):
        """Test getting non-existent job."""
        response = await test_client.get("/api/v1/jobs/99999")
        
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]
    
    async def test_create_job(self, test_client: AsyncClient, sample_job_data):
        """Test creating a new job."""
        job_data = {
            "title": sample_job_data["title"],
            "company_name": sample_job_data["company_name"],
            "location": sample_job_data["location"],
            "description": sample_job_data["description"],
            "requirements": sample_job_data["requirements"],
            "salary_min": sample_job_data["salary_min"],
            "salary_max": sample_job_data["salary_max"],
            "currency": sample_job_data["salary_currency"],
            "source_url": sample_job_data["source_url"],
            "source_platform": sample_job_data["source_platform"],
            "job_level": sample_job_data["experience_level"],
            "employment_type": sample_job_data["job_type"],
            "remote_friendly": sample_job_data["is_remote"]
        }
        
        response = await test_client.post("/api/v1/jobs/", json=job_data)
        
        assert response.status_code == 201
        created_job = response.json()
        assert created_job["title"] == job_data["title"]
        assert created_job["company_name"] == job_data["company_name"]
        assert created_job["id"] is not None
    
    async def test_create_job_missing_required_fields(self, test_client: AsyncClient):
        """Test creating job with missing required fields."""
        incomplete_data = {
            "company_name": "Test Company"
            # Missing title, source_url, source_platform
        }
        
        response = await test_client.post("/api/v1/jobs/", json=incomplete_data)
        
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("title" in str(error) for error in errors)
    
    async def test_create_job_duplicate_url(self, test_client: AsyncClient, sample_job_in_db):
        """Test creating job with duplicate source URL."""
        duplicate_data = {
            "title": "Another Job",
            "company_name": "Another Company",
            "source_url": sample_job_in_db.source_url,  # Duplicate URL
            "source_platform": "indeed"
        }
        
        response = await test_client.post("/api/v1/jobs/", json=duplicate_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    async def test_update_job(self, test_client: AsyncClient, sample_job_in_db):
        """Test updating an existing job."""
        update_data = {
            "title": "Updated Job Title",
            "description": "Updated job description",
            "ai_fit_score": 90
        }
        
        response = await test_client.put(
            f"/api/v1/jobs/{sample_job_in_db.id}",
            json=update_data
        )
        
        assert response.status_code == 200
        updated_job = response.json()
        assert updated_job["title"] == "Updated Job Title"
        assert updated_job["description"] == "Updated job description"
        assert updated_job["ai_fit_score"] == 90
    
    async def test_update_job_not_found(self, test_client: AsyncClient):
        """Test updating non-existent job."""
        update_data = {"title": "Updated Title"}
        
        response = await test_client.put("/api/v1/jobs/99999", json=update_data)
        
        assert response.status_code == 404
    
    async def test_delete_job(self, test_client: AsyncClient, sample_job_in_db):
        """Test deleting a job (soft delete)."""
        response = await test_client.delete(f"/api/v1/jobs/{sample_job_in_db.id}")
        
        assert response.status_code == 200
        
        # Verify job is soft deleted (is_active = False)
        get_response = await test_client.get(f"/api/v1/jobs/{sample_job_in_db.id}")
        assert get_response.status_code == 404  # Should not be found in active jobs
    
    async def test_delete_job_not_found(self, test_client: AsyncClient):
        """Test deleting non-existent job."""
        response = await test_client.delete("/api/v1/jobs/99999")
        
        assert response.status_code == 404
    
    async def test_search_jobs_by_title(self, test_client: AsyncClient, test_db):
        """Test searching jobs by title."""
        # Create test jobs
        jobs_data = [
            {"title": "Product Manager", "company": "Company A"},
            {"title": "Senior Product Manager", "company": "Company B"},
            {"title": "Business Analyst", "company": "Company C"}
        ]
        
        for job_data in jobs_data:
            job = Job(
                title=job_data["title"],
                company_name=job_data["company"],
                source_url=f"https://example.com/{job_data['title'].replace(' ', '_').lower()}",
                source_platform="indeed"
            )
            test_db.add(job)
        await test_db.commit()
        
        # Search for "Product" jobs
        response = await test_client.get("/api/v1/jobs/search?q=Product")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = [job["title"] for job in data["jobs"]]
        assert "Product Manager" in titles
        assert "Senior Product Manager" in titles
        assert "Business Analyst" not in titles
    
    async def test_filter_jobs_by_company(self, test_client: AsyncClient, test_db):
        """Test filtering jobs by company."""
        # Create test jobs
        companies = ["Google", "Microsoft", "Apple"]
        for i, company in enumerate(companies):
            job = Job(
                title=f"Job {i+1}",
                company_name=company,
                source_url=f"https://example.com/job{i+1}",
                source_platform="indeed"
            )
            test_db.add(job)
        await test_db.commit()
        
        # Filter by Google
        response = await test_client.get("/api/v1/jobs/?company=Google")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["company_name"] == "Google"
    
    async def test_filter_jobs_by_salary_range(self, test_client: AsyncClient, test_db):
        """Test filtering jobs by salary range."""
        # Create jobs with different salaries
        salary_ranges = [
            (80000, 100000),
            (120000, 150000),
            (160000, 200000)
        ]
        
        for i, (min_sal, max_sal) in enumerate(salary_ranges):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i+1}",
                salary_min=min_sal,
                salary_max=max_sal,
                source_url=f"https://example.com/job{i+1}",
                source_platform="indeed"
            )
            test_db.add(job)
        await test_db.commit()
        
        # Filter by minimum salary
        response = await test_client.get("/api/v1/jobs/?min_salary=120000")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # Jobs 2 and 3
        
        for job in data["jobs"]:
            assert job["salary_min"] >= 120000
    
    async def test_filter_jobs_by_location(self, test_client: AsyncClient, test_db):
        """Test filtering jobs by location."""
        locations = ["San Francisco, CA", "New York, NY", "Remote"]
        
        for i, location in enumerate(locations):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i+1}",
                location=location,
                source_url=f"https://example.com/job{i+1}",
                source_platform="indeed"
            )
            test_db.add(job)
        await test_db.commit()
        
        # Filter by San Francisco
        response = await test_client.get("/api/v1/jobs/?location=San Francisco")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "San Francisco" in data["jobs"][0]["location"]
    
    async def test_filter_jobs_by_remote(self, test_client: AsyncClient, test_db):
        """Test filtering remote jobs."""
        job_configs = [
            {"title": "Remote Job", "remote": True},
            {"title": "Office Job", "remote": False}
        ]
        
        for i, config in enumerate(job_configs):
            job = Job(
                title=config["title"],
                company_name=f"Company {i+1}",
                remote_friendly=config["remote"],
                source_url=f"https://example.com/job{i+1}",
                source_platform="indeed"
            )
            test_db.add(job)
        await test_db.commit()
        
        # Filter remote jobs
        response = await test_client.get("/api/v1/jobs/?remote=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["remote_friendly"] is True
    
    async def test_pagination(self, test_client: AsyncClient, test_db):
        """Test job listing pagination."""
        # Create 25 test jobs
        for i in range(25):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i+1}",
                source_url=f"https://example.com/job{i+1}",
                source_platform="indeed"
            )
            test_db.add(job)
        await test_db.commit()
        
        # Test first page
        response = await test_client.get("/api/v1/jobs/?page=1&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["jobs"]) == 10
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 3
        
        # Test second page
        response = await test_client.get("/api/v1/jobs/?page=2&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 10
        assert data["page"] == 2
        
        # Test last page
        response = await test_client.get("/api/v1/jobs/?page=3&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 5  # Remaining jobs
        assert data["page"] == 3
    
    async def test_sort_jobs(self, test_client: AsyncClient, test_db):
        """Test sorting jobs."""
        # Create jobs with different posted dates
        base_time = datetime.now(timezone.utc)
        for i in range(3):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i+1}",
                salary_min=100000 + (i * 20000),
                posted_date=base_time.replace(day=i+1),
                source_url=f"https://example.com/job{i+1}",
                source_platform="indeed"
            )
            test_db.add(job)
        await test_db.commit()
        
        # Sort by salary descending
        response = await test_client.get("/api/v1/jobs/?sort_by=salary_min&sort_order=desc")
        
        assert response.status_code == 200
        data = response.json()
        salaries = [job["salary_min"] for job in data["jobs"]]
        assert salaries == sorted(salaries, reverse=True)
        
        # Sort by posted date ascending
        response = await test_client.get("/api/v1/jobs/?sort_by=posted_date&sort_order=asc")
        
        assert response.status_code == 200
        data = response.json()
        # Verify chronological order (first job should have earliest date)
        assert len(data["jobs"]) == 3
    
    async def test_get_job_stats(self, test_client: AsyncClient, test_db):
        """Test getting job statistics."""
        # Create jobs with various attributes
        job_configs = [
            {"platform": "indeed", "remote": True, "salary": 100000},
            {"platform": "indeed", "remote": False, "salary": 120000},
            {"platform": "linkedin", "remote": True, "salary": 140000}
        ]
        
        for i, config in enumerate(job_configs):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i+1}",
                source_platform=config["platform"],
                remote_friendly=config["remote"],
                salary_min=config["salary"],
                source_url=f"https://example.com/job{i+1}"
            )
            test_db.add(job)
        await test_db.commit()
        
        response = await test_client.get("/api/v1/jobs/stats")
        
        assert response.status_code == 200
        stats = response.json()
        
        assert stats["total_jobs"] == 3
        assert stats["remote_jobs"] == 2
        assert stats["platform_breakdown"]["indeed"] == 2
        assert stats["platform_breakdown"]["linkedin"] == 1
        assert stats["avg_salary"] > 0
    
    async def test_bulk_update_jobs(self, test_client: AsyncClient, test_db):
        """Test bulk updating jobs."""
        # Create test jobs
        job_ids = []
        for i in range(3):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i+1}",
                source_url=f"https://example.com/job{i+1}",
                source_platform="indeed"
            )
            test_db.add(job)
            await test_db.flush()
            job_ids.append(job.id)
        await test_db.commit()
        
        # Bulk update
        update_data = {
            "job_ids": job_ids,
            "updates": {
                "ai_fit_score": 85,
                "is_active": True
            }
        }
        
        response = await test_client.put("/api/v1/jobs/bulk", json=update_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["updated_count"] == 3
        
        # Verify updates
        for job_id in job_ids:
            response = await test_client.get(f"/api/v1/jobs/{job_id}")
            job = response.json()
            assert job["ai_fit_score"] == 85