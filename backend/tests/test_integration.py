"""
Integration tests for the MBA Job Hunter system.

Tests end-to-end workflows combining multiple components
including scraping, AI analysis, and Notion integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.scrapers.indeed import IndeedScraper
from app.services.notion_writer import NotionWriter
from app.services.ai_services import JobAnalyzer, JobFitScorer
from app.models.job import Job
from app.models.company import Company


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobScrapingIntegration:
    """Test integration between scraping and database."""
    
    async def test_scrape_and_store_workflow(self, test_db, mock_httpx_client):
        """Test complete scraping and database storage workflow."""
        # Mock scraper HTTP response
        mock_html = """
        <html>
            <body>
                <div data-jk="job123">
                    <h2 class="jobTitle">Senior Product Manager</h2>
                    <span class="companyName">TechCorp</span>
                    <div data-testid="job-location">San Francisco, CA</div>
                    <span class="salaryText">$150,000 - $200,000</span>
                    <div class="job-snippet">Excellent MBA opportunity in tech</div>
                </div>
            </body>
        </html>
        """
        
        mock_httpx_client.get.return_value.content = mock_html.encode()
        mock_httpx_client.get.return_value.text = mock_html
        mock_httpx_client.get.return_value.status_code = 200
        
        with patch('app.scrapers.indeed.httpx.AsyncClient', return_value=mock_httpx_client):
            scraper = IndeedScraper()
            
            # Simulate job extraction (simplified)
            job_data = {
                "title": "Senior Product Manager",
                "company_name": "TechCorp",
                "location": "San Francisco, CA",
                "description": "Excellent MBA opportunity in tech",
                "salary_min": 150000,
                "salary_max": 200000,
                "source_url": "https://indeed.com/job/123",
                "source_platform": "indeed"
            }
            
            # Store in database
            job = Job(**job_data)
            test_db.add(job)
            await test_db.commit()
            await test_db.refresh(job)
            
            assert job.id is not None
            assert job.title == "Senior Product Manager"
            assert job.salary_min == 150000
    
    async def test_scrape_analyze_store_workflow(self, test_db, mock_openai_service):
        """Test scraping, AI analysis, and storage workflow."""
        # Mock AI analysis
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "Strong MBA relevance",
            "skills": ["Strategy", "Leadership", "MBA"]
        }
        mock_openai_service.extract_skills.return_value = [
            "Product Management", "Strategy", "Leadership", "MBA"
        ]
        
        # Create job data
        job_data = {
            "title": "Product Manager - MBA Required",
            "company_name": "Top Consulting Firm",
            "location": "New York, NY",
            "description": "Looking for MBA graduate with consulting background",
            "requirements": "MBA from top-tier school required",
            "source_url": "https://indeed.com/job/456",
            "source_platform": "indeed"
        }
        
        # Initialize services
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        scorer = JobFitScorer()
        
        # Run AI analysis
        ai_result = await analyzer.analyze_job(
            job_data["title"],
            job_data["description"]
        )
        
        fit_score = await scorer.calculate_fit_score(job_data)
        
        # Store with AI results
        job = Job(
            **job_data,
            ai_fit_score=int(fit_score),
            extracted_skills=ai_result["skills"],
            ai_analysis=ai_result["reasoning"]
        )
        
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        assert job.id is not None
        assert job.ai_fit_score == int(fit_score)
        assert "MBA" in job.extracted_skills
        assert job.ai_analysis == "Strong MBA relevance"


@pytest.mark.integration
@pytest.mark.asyncio
class TestNotionIntegration:
    """Test integration with Notion API."""
    
    async def test_job_to_notion_workflow(self, test_db, mock_notion_client, sample_job_data):
        """Test complete job to Notion workflow."""
        # Create and store job
        job = Job(**sample_job_data)
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # Initialize Notion writer
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock Notion responses
        mock_notion_client.databases.query.return_value = {"results": []}
        mock_notion_client.pages.create.return_value = {"id": "notion_page_123"}
        
        # Write to Notion
        page_id = await writer.write_job_to_notion(sample_job_data)
        
        assert page_id == "notion_page_123"
        mock_notion_client.pages.create.assert_called_once()
        
        # Verify call structure
        call_args = mock_notion_client.pages.create.call_args
        assert "parent" in call_args.kwargs
        assert "properties" in call_args.kwargs
        assert "children" in call_args.kwargs
    
    async def test_batch_job_sync_workflow(self, test_db, mock_notion_client, sample_job_list):
        """Test batch job synchronization with Notion."""
        # Create jobs in database
        jobs = []
        for job_data in sample_job_list:
            job = Job(**job_data)
            jobs.append(job)
            test_db.add(job)
        
        await test_db.commit()
        for job in jobs:
            await test_db.refresh(job)
        
        # Initialize Notion writer
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Mock Notion responses
        mock_notion_client.databases.query.return_value = {"results": []}
        mock_notion_client.pages.create.return_value = {"id": "notion_page_123"}
        
        # Batch write
        page_ids = await writer.batch_write_jobs(sample_job_list)
        
        assert len(page_ids) == len(sample_job_list)
        assert mock_notion_client.pages.create.call_count == len(sample_job_list)
        
        # Check writer stats
        stats = writer.get_stats()
        assert stats["jobs_written"] == len(sample_job_list)


@pytest.mark.integration
@pytest.mark.asyncio
class TestFullWorkflowIntegration:
    """Test complete end-to-end workflows."""
    
    async def test_complete_job_processing_pipeline(
        self, 
        test_db, 
        mock_httpx_client, 
        mock_notion_client, 
        mock_openai_service
    ):
        """Test complete job processing from scraping to Notion."""
        # 1. Mock scraping
        mock_html = """
        <html>
            <body>
                <div data-jk="job789">
                    <h2 class="jobTitle">Strategy Consultant</h2>
                    <span class="companyName">McKinsey & Company</span>
                    <div data-testid="job-location">Boston, MA</div>
                    <span class="salaryText">$180,000 - $220,000</span>
                    <div class="job-snippet">MBA required, strategy consulting role</div>
                </div>
            </body>
        </html>
        """
        
        mock_httpx_client.get.return_value.content = mock_html.encode()
        mock_httpx_client.get.return_value.text = mock_html
        mock_httpx_client.get.return_value.status_code = 200
        
        # 2. Mock AI analysis
        mock_openai_service.analyze_job_description.return_value = {
            "score": 95,
            "reasoning": "Perfect MBA fit - strategy consulting at top firm",
            "skills": ["Strategy", "Consulting", "MBA", "Leadership"]
        }
        mock_openai_service.extract_skills.return_value = [
            "Strategy", "Consulting", "MBA", "Leadership", "Problem Solving"
        ]
        
        # 3. Mock Notion
        mock_notion_client.databases.query.return_value = {"results": []}
        mock_notion_client.pages.create.return_value = {"id": "notion_page_789"}
        
        # 4. Process job data
        scraped_job_data = {
            "title": "Strategy Consultant",
            "company_name": "McKinsey & Company",
            "location": "Boston, MA",
            "description": "MBA required, strategy consulting role",
            "salary_min": 180000,
            "salary_max": 220000,
            "source_url": "https://indeed.com/job/789",
            "source_platform": "indeed"
        }
        
        # 5. AI Analysis
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        scorer = JobFitScorer()
        
        ai_result = await analyzer.analyze_job(
            scraped_job_data["title"],
            scraped_job_data["description"]
        )
        
        fit_score = await scorer.calculate_fit_score(scraped_job_data)
        
        # 6. Store in database
        job = Job(
            **scraped_job_data,
            ai_fit_score=int(fit_score),
            extracted_skills=ai_result["skills"],
            ai_analysis=ai_result["reasoning"]
        )
        
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # 7. Sync to Notion
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Prepare job data for Notion (convert from DB model)
        notion_job_data = {
            "title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "description": job.description,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.currency or "USD",
            "source_url": job.source_url,
            "source_platform": job.source_platform,
            "relevance_score": job.ai_fit_score / 100,  # Convert to 0-1 scale
            "skills_required": job.extracted_skills or [],
            "ai_fit_score": job.ai_fit_score
        }
        
        page_id = await writer.write_job_to_notion(notion_job_data)
        
        # 8. Verify complete workflow
        assert job.id is not None
        assert job.title == "Strategy Consultant"
        assert job.ai_fit_score == int(fit_score)
        assert "MBA" in job.extracted_skills
        assert page_id == "notion_page_789"
        
        # Verify all services were called
        mock_openai_service.analyze_job_description.assert_called_once()
        mock_notion_client.pages.create.assert_called_once()
    
    async def test_error_recovery_workflow(
        self, 
        test_db, 
        mock_openai_service, 
        mock_anthropic_service, 
        mock_notion_client
    ):
        """Test error recovery in complete workflow."""
        # Setup partial failures
        mock_openai_service.analyze_job_description.side_effect = Exception("OpenAI API error")
        mock_anthropic_service.analyze_job_description.return_value = {
            "score": 80,
            "reasoning": "Good MBA fit (fallback analysis)",
            "skills": ["Strategy", "Leadership"]
        }
        
        # Job data
        job_data = {
            "title": "Business Analyst",
            "company_name": "Consulting Firm",
            "location": "Chicago, IL",
            "description": "MBA opportunity in business analysis",
            "source_url": "https://indeed.com/job/999",
            "source_platform": "indeed"
        }
        
        # Test fallback behavior
        analyzer = JobAnalyzer(
            openai_service=mock_openai_service,
            anthropic_service=mock_anthropic_service
        )
        
        # Should fallback to Anthropic
        ai_result = await analyzer.analyze_job(
            job_data["title"],
            job_data["description"]
        )
        
        assert ai_result["score"] == 80
        assert ai_result["service_used"] == "anthropic"
        assert "fallback" in ai_result["reasoning"]
        
        # Scorer should still work
        scorer = JobFitScorer()
        fit_score = await scorer.calculate_fit_score(job_data)
        assert isinstance(fit_score, (int, float))
        
        # Store job even with partial failure
        job = Job(
            **job_data,
            ai_fit_score=int(fit_score),
            extracted_skills=ai_result["skills"],
            ai_analysis=ai_result["reasoning"]
        )
        
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        assert job.id is not None
        assert job.ai_analysis == "Good MBA fit (fallback analysis)"
    
    async def test_performance_workflow(self, test_db, mock_openai_service):
        """Test performance with multiple jobs."""
        # Create multiple jobs
        job_count = 10
        jobs_data = []
        
        for i in range(job_count):
            job_data = {
                "title": f"Product Manager {i+1}",
                "company_name": f"Company {i+1}",
                "location": "San Francisco, CA",
                "description": f"MBA role {i+1} with strategy focus",
                "source_url": f"https://indeed.com/job/{i+1}",
                "source_platform": "indeed"
            }
            jobs_data.append(job_data)
        
        # Mock AI service
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "Good MBA fit",
            "skills": ["Strategy", "Leadership", "MBA"]
        }
        
        # Batch process
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        scorer = JobFitScorer()
        
        # Time the analysis
        import time
        start_time = time.time()
        
        # Process all jobs
        for job_data in jobs_data:
            ai_result = await analyzer.analyze_job(
                job_data["title"],
                job_data["description"]
            )
            
            fit_score = await scorer.calculate_fit_score(job_data)
            
            job = Job(
                **job_data,
                ai_fit_score=int(fit_score),
                extracted_skills=ai_result["skills"],
                ai_analysis=ai_result["reasoning"]
            )
            
            test_db.add(job)
        
        await test_db.commit()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all jobs were processed
        from sqlalchemy import select
        result = await test_db.execute(select(Job))
        all_jobs = result.scalars().all()
        
        assert len(all_jobs) == job_count
        assert processing_time < 30  # Should complete within 30 seconds
        
        # Verify AI service was called for each job
        assert mock_openai_service.analyze_job_description.call_count == job_count


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Test database integration scenarios."""
    
    async def test_job_company_relationship(self, test_db):
        """Test job and company relationship handling."""
        # Create company
        company = Company(
            name="Tech Giant Corp",
            industry="Technology",
            size="10000+",
            location="San Francisco, CA",
            glassdoor_rating=4.5
        )
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)
        
        # Create job referencing company
        job = Job(
            title="Senior Product Manager",
            company_name="Tech Giant Corp",  # Should match company.name
            location="San Francisco, CA",
            description="Great MBA opportunity",
            source_url="https://indeed.com/job/company-test",
            source_platform="indeed"
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)
        
        # Verify both exist
        assert company.id is not None
        assert job.id is not None
        assert job.company_name == company.name
        
        # Test queries
        from sqlalchemy import select
        
        # Find jobs by company
        result = await test_db.execute(
            select(Job).where(Job.company_name == company.name)
        )
        company_jobs = result.scalars().all()
        
        assert len(company_jobs) == 1
        assert company_jobs[0].id == job.id
    
    async def test_bulk_operations(self, test_db):
        """Test bulk database operations."""
        # Create multiple jobs
        jobs = []
        for i in range(50):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i+1}",
                location="Various",
                description=f"Description {i+1}",
                source_url=f"https://indeed.com/job/bulk-{i+1}",
                source_platform="indeed",
                ai_fit_score=70 + (i % 30)  # Varying scores
            )
            jobs.append(job)
            test_db.add(job)
        
        await test_db.commit()
        
        # Test bulk queries
        from sqlalchemy import select, func
        
        # Count all jobs
        result = await test_db.execute(select(func.count(Job.id)))
        total_jobs = result.scalar()
        assert total_jobs == 50
        
        # Filter by score range
        result = await test_db.execute(
            select(Job).where(Job.ai_fit_score >= 90)
        )
        high_score_jobs = result.scalars().all()
        assert len(high_score_jobs) > 0
        
        # Test pagination
        result = await test_db.execute(
            select(Job).limit(10).offset(20)
        )
        page_jobs = result.scalars().all()
        assert len(page_jobs) == 10
