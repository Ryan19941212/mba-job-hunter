"""
Performance tests for the MBA Job Hunter system.

Tests system performance under load and measures
response times for critical operations.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.scrapers.indeed import IndeedScraper
from app.services.notion_writer import NotionWriter
from app.services.ai_services import JobAnalyzer, JobFitScorer
from app.models.job import Job
from sqlalchemy import select, func


@pytest.mark.performance
@pytest.mark.asyncio
class TestScrapingPerformance:
    """Test scraping performance."""
    
    async def test_single_page_scraping_speed(self, mock_httpx_client):
        """Test single page scraping performance."""
        # Mock HTML response
        mock_html = """
        <html><body>
        """ + "".join([
            f"""
            <div data-jk="job{i}">
                <h2 class="jobTitle">Job {i}</h2>
                <span class="companyName">Company {i}</span>
                <div data-testid="job-location">Location {i}</div>
                <div class="job-snippet">Description {i}</div>
            </div>
            """ for i in range(50)  # 50 jobs per page
        ]) + "</body></html>"
        
        mock_httpx_client.get.return_value.content = mock_html.encode()
        mock_httpx_client.get.return_value.text = mock_html
        mock_httpx_client.get.return_value.status_code = 200
        
        with patch('app.scrapers.indeed.httpx.AsyncClient', return_value=mock_httpx_client):
            scraper = IndeedScraper()
            
            start_time = time.time()
            
            # Simulate page processing
            jobs_count = 0
            async for job in scraper.search_jobs("Product Manager", "San Francisco"):
                jobs_count += 1
                if jobs_count >= 50:  # Process one page
                    break
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Should process 50 jobs in under 10 seconds
            assert processing_time < 10.0
            assert jobs_count == 50
    
    async def test_concurrent_scraping(self, mock_httpx_client):
        """Test concurrent scraping performance."""
        mock_html = "<html><body><div data-jk='job1'><h2 class='jobTitle'>Test Job</h2></div></body></html>"
        mock_httpx_client.get.return_value.content = mock_html.encode()
        mock_httpx_client.get.return_value.text = mock_html
        mock_httpx_client.get.return_value.status_code = 200
        
        async def scrape_search_term(term):
            with patch('app.scrapers.indeed.httpx.AsyncClient', return_value=mock_httpx_client):
                scraper = IndeedScraper()
                jobs = []
                async for job in scraper.search_jobs(term, "San Francisco"):
                    jobs.append(job)
                    if len(jobs) >= 10:  # Limit for testing
                        break
                return jobs
        
        search_terms = [
            "Product Manager",
            "Business Analyst", 
            "Strategy Consultant",
            "Project Manager",
            "Data Analyst"
        ]
        
        start_time = time.time()
        
        # Run concurrent searches
        tasks = [scrape_search_term(term) for term in search_terms]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete all searches in under 30 seconds
        assert total_time < 30.0
        assert len(results) == len(search_terms)
        
        total_jobs = sum(len(jobs) for jobs in results)
        assert total_jobs > 0
    
    async def test_rate_limiting_performance(self):
        """Test that rate limiting doesn't severely impact performance."""
        from app.scrapers.base import ScrapingConfig
        
        config = ScrapingConfig(
            rate_limit_per_minute=60,  # 1 request per second
            delay_between_requests=0.1
        )
        
        scraper = IndeedScraper(config)
        
        start_time = time.time()
        
        # Simulate multiple rate limit checks
        for _ in range(10):
            await scraper._rate_limit_check()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete quickly even with rate limiting
        assert total_time < 5.0


@pytest.mark.performance
@pytest.mark.asyncio
class TestDatabasePerformance:
    """Test database performance."""
    
    async def test_bulk_job_insertion(self, test_db):
        """Test bulk job insertion performance."""
        job_count = 1000
        
        start_time = time.time()
        
        # Create jobs in batches
        batch_size = 100
        for batch_start in range(0, job_count, batch_size):
            batch_jobs = []
            
            for i in range(batch_start, min(batch_start + batch_size, job_count)):
                job = Job(
                    title=f"Job {i+1}",
                    company_name=f"Company {i+1}",
                    location="San Francisco, CA",
                    description=f"Description for job {i+1}",
                    source_url=f"https://indeed.com/job/{i+1}",
                    source_platform="indeed",
                    ai_fit_score=50 + (i % 50)
                )
                batch_jobs.append(job)
                test_db.add(job)
            
            await test_db.commit()
        
        end_time = time.time()
        insertion_time = end_time - start_time
        
        # Should insert 1000 jobs in under 30 seconds
        assert insertion_time < 30.0
        
        # Verify all jobs were inserted
        result = await test_db.execute(select(func.count(Job.id)))
        total_jobs = result.scalar()
        assert total_jobs == job_count
    
    async def test_complex_query_performance(self, test_db):
        """Test complex query performance."""
        # First insert test data
        job_count = 500
        for i in range(job_count):
            job = Job(
                title=f"Job {i+1}",
                company_name=f"Company {i % 50}",  # 50 different companies
                location=f"City {i % 10}",  # 10 different cities
                description=f"Description {i+1}",
                salary_min=50000 + (i * 100),
                salary_max=80000 + (i * 100),
                source_url=f"https://indeed.com/job/{i+1}",
                source_platform="indeed",
                ai_fit_score=i % 100,
                extracted_skills=[f"Skill{j}" for j in range(i % 5 + 1)]
            )
            test_db.add(job)
        
        await test_db.commit()
        
        # Test complex queries
        queries = [
            # Filter by salary range
            select(Job).where(Job.salary_min >= 70000, Job.salary_max <= 150000),
            
            # Filter by AI fit score
            select(Job).where(Job.ai_fit_score >= 80),
            
            # Filter by company and location
            select(Job).where(Job.company_name.like("Company 1%"), Job.location.like("City%")),
            
            # Pagination with sorting
            select(Job).order_by(Job.ai_fit_score.desc()).limit(20).offset(100),
            
            # Count aggregation
            select(func.count(Job.id)).where(Job.ai_fit_score >= 75)
        ]
        
        start_time = time.time()
        
        for query in queries:
            result = await test_db.execute(query)
            if "count" in str(query):
                result.scalar()
            else:
                result.scalars().all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # All queries should complete in under 5 seconds
        assert query_time < 5.0
    
    async def test_concurrent_database_operations(self, test_db):
        """Test concurrent database operations."""
        async def insert_jobs(start_idx, count):
            jobs = []
            for i in range(start_idx, start_idx + count):
                job = Job(
                    title=f"Job {i}",
                    company_name=f"Company {i}",
                    source_url=f"https://indeed.com/job/{i}",
                    source_platform="indeed"
                )
                jobs.append(job)
                test_db.add(job)
            
            await test_db.commit()
            return len(jobs)
        
        start_time = time.time()
        
        # Run concurrent insertions
        tasks = [
            insert_jobs(0, 50),
            insert_jobs(50, 50),
            insert_jobs(100, 50),
            insert_jobs(150, 50)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete in under 15 seconds
        assert total_time < 15.0
        assert sum(results) == 200
        
        # Verify total count
        result = await test_db.execute(select(func.count(Job.id)))
        total_jobs = result.scalar()
        assert total_jobs == 200


@pytest.mark.performance
@pytest.mark.asyncio
class TestAIServicePerformance:
    """Test AI service performance."""
    
    async def test_batch_job_analysis_performance(self, mock_openai_service):
        """Test batch job analysis performance."""
        # Mock AI service responses
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "Good MBA fit",
            "skills": ["Strategy", "Leadership"]
        }
        
        # Create test jobs
        job_count = 100
        jobs_data = []
        for i in range(job_count):
            job_data = {
                "title": f"Product Manager {i+1}",
                "description": f"MBA opportunity {i+1} with consulting background",
                "company_name": f"Company {i+1}"
            }
            jobs_data.append(job_data)
        
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        
        start_time = time.time()
        
        # Analyze all jobs
        tasks = [
            analyzer.analyze_job(job["title"], job["description"])
            for job in jobs_data
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        analysis_time = end_time - start_time
        
        # Should complete in under 30 seconds (with mocking)
        assert analysis_time < 30.0
        assert len(results) == job_count
        
        # Verify all analyses completed
        for result in results:
            assert result["score"] == 85
            assert "reasoning" in result
    
    async def test_fit_scoring_performance(self):
        """Test job fit scoring performance."""
        scorer = JobFitScorer()
        
        # Create test jobs with varying complexity
        jobs_data = []
        for i in range(200):
            complexity = i % 3
            if complexity == 0:  # Simple job
                job_data = {
                    "title": f"Job {i+1}",
                    "description": "Short description",
                    "company_name": f"Company {i+1}"
                }
            elif complexity == 1:  # Medium job
                job_data = {
                    "title": f"Product Manager {i+1}",
                    "description": "MBA opportunity with strategy consulting background " * 5,
                    "company_name": f"Consulting Firm {i+1}",
                    "requirements": "MBA required, 3+ years experience"
                }
            else:  # Complex job
                job_data = {
                    "title": f"Senior Strategy Consultant {i+1}",
                    "description": "Extensive MBA opportunity with detailed requirements " * 20,
                    "company_name": f"Top Consulting Firm {i+1}",
                    "requirements": "MBA from top-tier school required " * 10,
                    "location": "Multiple locations worldwide"
                }
            
            jobs_data.append(job_data)
        
        start_time = time.time()
        
        # Score all jobs
        tasks = [scorer.calculate_fit_score(job_data) for job_data in jobs_data]
        scores = await asyncio.gather(*tasks)
        
        end_time = time.time()
        scoring_time = end_time - start_time
        
        # Should complete in under 10 seconds
        assert scoring_time < 10.0
        assert len(scores) == 200
        
        # Verify all scores are valid
        for score in scores:
            assert 0 <= score <= 100
    
    async def test_concurrent_ai_operations(self, mock_openai_service, mock_anthropic_service):
        """Test concurrent AI operations performance."""
        # Mock responses
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "OpenAI analysis",
            "skills": ["Strategy"]
        }
        mock_anthropic_service.analyze_job_description.return_value = {
            "score": 90,
            "reasoning": "Anthropic analysis",
            "skills": ["Leadership"]
        }
        
        analyzer = JobAnalyzer(
            openai_service=mock_openai_service,
            anthropic_service=mock_anthropic_service
        )
        scorer = JobFitScorer()
        
        job_data = {
            "title": "Product Manager",
            "description": "MBA opportunity with consulting background",
            "company_name": "Tech Company"
        }
        
        start_time = time.time()
        
        # Run operations concurrently
        tasks = [
            analyzer.analyze_job(job_data["title"], job_data["description"], service="openai"),
            analyzer.analyze_job(job_data["title"], job_data["description"], service="anthropic"),
            scorer.calculate_fit_score(job_data),
            scorer.calculate_fit_score(job_data),
            scorer.calculate_fit_score(job_data)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete quickly with concurrent execution
        assert total_time < 5.0
        assert len(results) == 5
        
        # Verify results
        assert results[0]["service_used"] == "openai"
        assert results[1]["service_used"] == "anthropic"
        for i in range(2, 5):
            assert isinstance(results[i], (int, float))


@pytest.mark.performance
@pytest.mark.asyncio
class TestNotionPerformance:
    """Test Notion integration performance."""
    
    async def test_batch_notion_writing_performance(self, mock_notion_client, sample_job_list):
        """Test batch Notion writing performance."""
        # Mock Notion responses
        mock_notion_client.databases.query.return_value = {"results": []}
        mock_notion_client.pages.create.return_value = {"id": "test_page_id"}
        
        writer = NotionWriter(api_key="test_key", database_id="test_db")
        writer.client = mock_notion_client
        
        # Create larger job list for performance testing
        large_job_list = []
        for i in range(50):
            job_data = sample_job_list[i % len(sample_job_list)].copy()
            job_data["source_url"] = f"https://indeed.com/job/perf-{i}"
            job_data["title"] = f"Job {i+1}"
            large_job_list.append(job_data)
        
        start_time = time.time()
        
        # Batch write
        page_ids = await writer.batch_write_jobs(large_job_list)
        
        end_time = time.time()
        writing_time = end_time - start_time
        
        # Should complete in under 30 seconds
        assert writing_time < 30.0
        assert len(page_ids) == 50
        assert mock_notion_client.pages.create.call_count == 50
    
    async def test_notion_formatting_performance(self, sample_job_data):
        """Test Notion data formatting performance."""
        writer = NotionWriter(api_key="test_key")
        
        # Create complex job data
        complex_job_data = sample_job_data.copy()
        complex_job_data["description"] = "Very long description " * 1000
        complex_job_data["requirements"] = "Detailed requirements " * 500
        complex_job_data["skills_required"] = [f"Skill {i}" for i in range(100)]
        
        start_time = time.time()
        
        # Format multiple times
        for _ in range(20):
            formatted = await writer.format_job_for_notion(complex_job_data)
            assert "properties" in formatted
            assert "children" in formatted
        
        end_time = time.time()
        formatting_time = end_time - start_time
        
        # Should complete in under 5 seconds
        assert formatting_time < 5.0


@pytest.mark.performance
@pytest.mark.asyncio
class TestMemoryUsage:
    """Test memory usage patterns."""
    
    async def test_large_dataset_memory_usage(self, test_db):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and process large number of jobs
        job_count = 2000
        batch_size = 200
        
        for batch_start in range(0, job_count, batch_size):
            batch_jobs = []
            for i in range(batch_start, min(batch_start + batch_size, job_count)):
                job = Job(
                    title=f"Memory Test Job {i+1}",
                    company_name=f"Company {i+1}",
                    description="Description " * 100,  # Larger description
                    source_url=f"https://indeed.com/job/memory-{i+1}",
                    source_platform="indeed",
                    extracted_skills=[f"Skill{j}" for j in range(20)]  # Many skills
                )
                batch_jobs.append(job)
                test_db.add(job)
            
            await test_db.commit()
            
            # Clear Python references
            del batch_jobs
        
        # Query back data
        result = await test_db.execute(select(Job).limit(1000))
        jobs = result.scalars().all()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 500MB)
        assert memory_increase < 500
        assert len(jobs) == 1000
    
    async def test_concurrent_operations_memory(self, mock_openai_service):
        """Test memory usage during concurrent operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock AI service
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "Good fit " * 100,  # Large response
            "skills": [f"Skill {i}" for i in range(50)]
        }
        
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        scorer = JobFitScorer()
        
        # Create many concurrent operations
        tasks = []
        for i in range(100):
            job_data = {
                "title": f"Concurrent Job {i+1}",
                "description": "Long description " * 200,
                "company_name": f"Company {i+1}"
            }
            
            tasks.extend([
                analyzer.analyze_job(job_data["title"], job_data["description"]),
                scorer.calculate_fit_score(job_data)
            ])
        
        # Execute all tasks
        results = await asyncio.gather(*tasks)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 300
        assert len(results) == 200  # 100 jobs * 2 operations each
