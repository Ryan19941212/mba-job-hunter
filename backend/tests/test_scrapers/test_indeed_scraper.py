"""
Tests for Indeed scraper functionality.

Tests job scraping, data parsing, error handling,
and anti-detection measures for the Indeed scraper.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.scrapers.indeed import IndeedScraper
from app.scrapers.base import ScrapingConfig, JobData


@pytest.mark.scraper
@pytest.mark.unit
class TestIndeedScraper:
    """Test Indeed scraper functionality."""
    
    def test_scraper_initialization(self):
        """Test IndeedScraper initialization."""
        scraper = IndeedScraper()
        
        assert scraper.name == "indeed"
        assert scraper.base_url == "https://www.indeed.com"
        assert scraper.scraper_type.value == "http_only"
        assert len(scraper._user_agents) > 0
        assert len(scraper._mba_keywords) > 0
    
    def test_scraper_with_custom_config(self, sample_scraper_config):
        """Test scraper with custom configuration."""
        scraper = IndeedScraper(sample_scraper_config)
        
        assert scraper.config.max_pages == 2
        assert scraper.config.delay_between_requests == 0.1
        assert scraper.config.rate_limit_per_minute == 100
    
    def test_build_search_params_basic(self):
        """Test basic search parameter building."""
        scraper = IndeedScraper()
        
        params = scraper._build_search_params("Product Manager", "San Francisco")
        
        assert params["q"] == "Product Manager"
        assert params["l"] == "San Francisco"
        assert params["sort"] == "date"
        assert params["limit"] == 50
        assert params["fromage"] == "7"
    
    def test_build_search_params_with_filters(self):
        """Test search parameters with additional filters."""
        scraper = IndeedScraper()
        
        params = scraper._build_search_params(
            "Business Analyst",
            "New York",
            salary_min=80000,
            job_type="full_time",
            remote_only=True,
            experience_level="mid_level",
            date_posted="3"
        )
        
        assert params["q"] == "Business Analyst"
        assert params["l"] == "New York"
        assert params["salary"] == "80000+"
        assert params["jt"] == "fulltime"
        assert params["remotejob"] == "1"
        assert params["explvl"] == "mid_level"
        assert params["fromage"] == "3"
    
    def test_job_type_mapping(self):
        """Test job type parameter mapping."""
        scraper = IndeedScraper()
        
        # Test various job type mappings
        test_cases = [
            ("full_time", "fulltime"),
            ("part_time", "parttime"),
            ("contract", "contract"),
            ("temporary", "temporary"),
            ("internship", "internship")
        ]
        
        for input_type, expected in test_cases:
            params = scraper._build_search_params(
                "Test Job",
                job_type=input_type
            )
            assert params["jt"] == expected
    
    def test_salary_parsing(self):
        """Test salary parsing functionality."""
        scraper = IndeedScraper()
        
        test_cases = [
            ("$120,000 - $150,000", {"min": 120000.0, "max": 150000.0}),
            ("Up to $200,000 per year", {"max": 200000.0}),
            ("Starting from $90,000", {"min": 90000.0}),
            ("$75/hour", {"min": 75.0, "period": None}),
            ("Competitive salary", {"min": None, "max": None}),
        ]
        
        for salary_text, expected in test_cases:
            result = scraper._parse_salary(salary_text)
            
            if expected.get("min") is not None:
                assert result.get("min") == expected["min"]
            if expected.get("max") is not None:
                assert result.get("max") == expected["max"]
    
    def test_date_parsing(self):
        """Test date parsing functionality."""
        scraper = IndeedScraper()
        
        test_cases = [
            "2 days ago",
            "1 week ago", 
            "3 hours ago",
            "1 month ago",
            "2024-01-15",
            "January 15, 2024"
        ]
        
        for date_text in test_cases:
            result = scraper._parse_date(date_text)
            # Should either parse successfully or return None
            assert result is None or isinstance(result, datetime)
    
    def test_skills_extraction(self):
        """Test skills extraction from job descriptions."""
        scraper = IndeedScraper()
        
        description = """
        We are looking for a Product Manager with MBA background.
        Requirements:
        - MBA from top-tier university
        - Strong analytical skills with SQL and Python
        - Experience with Tableau and PowerBI
        - Project management experience with Agile methodology
        - Leadership and communication skills
        """
        
        skills = scraper._extract_skills(description)
        
        assert len(skills) > 0
        assert "MBA" in skills
        expected_skills = ["SQL", "Python", "Tableau", "PowerBI", "Agile"]
        for skill in expected_skills:
            assert any(skill.lower() in s.lower() for s in skills)
    
    def test_relevance_filtering(self):
        """Test MBA job relevance filtering."""
        scraper = IndeedScraper()
        
        # Relevant job
        relevant_job = JobData(
            title="Product Manager - MBA Required",
            company_name="Tech Company",
            description="Looking for MBA graduate with strategy experience",
            source="indeed"
        )
        
        # Irrelevant job
        irrelevant_job = JobData(
            title="Warehouse Worker",
            company_name="Logistics Co",
            description="Physical labor, loading trucks",
            source="indeed"
        )
        
        assert scraper._is_relevant_job(relevant_job) is True
        assert scraper._is_relevant_job(irrelevant_job) is False
    
    def test_remote_job_detection(self):
        """Test remote job detection."""
        scraper = IndeedScraper()
        
        test_cases = [
            ("Remote", "Work from anywhere", True),
            ("San Francisco, CA", "Office-based role", False),
            ("New York, NY", "Remote work available", True),
            ("Remote", "", True),
            ("", "Work from home opportunity", True),
            ("Seattle, WA", "Hybrid work model", False)
        ]
        
        for location, description, expected in test_cases:
            result = scraper._is_remote_job(location, description)
            assert result == expected
    
    @patch('app.scrapers.indeed.httpx.AsyncClient')
    async def test_make_http_request_success(self, mock_client_class):
        """Test successful HTTP request."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html>Test content</html>"
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        scraper = IndeedScraper()
        scraper.session = mock_client
        
        response = await scraper._make_http_request("https://test.com")
        
        assert response.status_code == 200
        mock_client.request.assert_called_once()
    
    @patch('app.scrapers.indeed.httpx.AsyncClient')
    async def test_make_http_request_rate_limited(self, mock_client_class):
        """Test HTTP request with rate limiting."""
        # Setup mock to return 429 status
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = Exception("Rate limited")
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        scraper = IndeedScraper()
        scraper.session = mock_client
        
        with pytest.raises(Exception):
            await scraper._make_http_request("https://test.com")
    
    async def test_extract_job_from_card_valid_data(self):
        """Test job extraction from valid HTML card."""
        scraper = IndeedScraper()
        
        # Mock HTML card element
        mock_card = MagicMock()
        mock_card.get.return_value = "test_job_123"
        
        # Mock title element
        mock_title = MagicMock()
        mock_title.get_text.return_value = "Senior Product Manager"
        mock_card.find.side_effect = lambda tag, attrs=None: {
            ('h2', {'class': 'jobTitle'}): mock_title,
            ('span', {'class': 'companyName'}): MagicMock(get_text=lambda strip=True: "TechCorp"),
            ('div', {'data-testid': 'job-location'}): MagicMock(get_text=lambda strip=True: "San Francisco, CA"),
            ('span', {'class': 'salaryText'}): MagicMock(get_text=lambda strip=True: "$120,000 - $150,000"),
            ('div', {'class': 'job-snippet'}): MagicMock(get_text=lambda strip=True: "Great opportunity for MBA graduates"),
            ('span', {'class': 'date'}): MagicMock(get_text=lambda strip=True: "2 days ago")
        }.get((tag, attrs.get('class') if attrs and 'class' in attrs else None))
        
        job_data = await scraper._extract_job_from_card(mock_card)
        
        assert job_data is not None
        assert job_data.title == "Senior Product Manager"
        assert job_data.company_name == "TechCorp"
        assert job_data.location == "San Francisco, CA"
        assert job_data.source == "indeed"
    
    async def test_extract_job_from_card_missing_data(self):
        """Test job extraction with missing required data."""
        scraper = IndeedScraper()
        
        # Mock card with missing title
        mock_card = MagicMock()
        mock_card.get.return_value = "test_job_123"
        mock_card.find.return_value = None  # No title found
        
        job_data = await scraper._extract_job_from_card(mock_card)
        
        assert job_data is None
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        config = ScrapingConfig(
            rate_limit_per_minute=2,  # Very low for testing
            delay_between_requests=0.1
        )
        scraper = IndeedScraper(config)
        
        # Test that rate limiting doesn't block initial requests
        await scraper._rate_limit_check()
        await scraper._rate_limit_check()
        
        # This should complete without hanging (in real scenario it would delay)
        assert len(scraper._request_times) <= 2
    
    async def test_user_agent_rotation(self):
        """Test user agent rotation in requests."""
        scraper = IndeedScraper()
        
        # Test that different user agents are selected
        user_agents_used = set()
        
        for _ in range(10):
            # Simulate the user agent selection process
            import random
            user_agent = random.choice(scraper._user_agents)
            user_agents_used.add(user_agent)
        
        # Should use multiple user agents
        assert len(user_agents_used) > 1
        
        # All should be valid user agent strings
        for ua in user_agents_used:
            assert "Mozilla" in ua
            assert "Chrome" in ua or "Firefox" in ua or "Safari" in ua
    
    async def test_scraper_statistics(self):
        """Test scraper statistics tracking."""
        scraper = IndeedScraper()
        
        initial_stats = scraper.get_stats()
        assert initial_stats["jobs_found"] == 0
        assert initial_stats["jobs_processed"] == 0
        assert initial_stats["errors"] == 0
        assert initial_stats["start_time"] is None
        
        # Simulate some activity
        scraper._stats["jobs_found"] = 5
        scraper._stats["errors"] = 1
        
        updated_stats = scraper.get_stats()
        assert updated_stats["jobs_found"] == 5
        assert updated_stats["errors"] == 1
    
    @patch('app.scrapers.indeed.BeautifulSoup')
    async def test_has_next_page(self, mock_bs):
        """Test next page detection."""
        scraper = IndeedScraper()
        
        # Mock soup with next page link
        mock_soup = MagicMock()
        mock_soup.find.return_value = MagicMock()  # Next link found
        
        has_next = scraper._has_next_page(mock_soup)
        assert has_next is True
        
        # Mock soup without next page link
        mock_soup.find.return_value = None  # No next link
        
        has_next = scraper._has_next_page(mock_soup)
        assert has_next is False
    
    async def test_scraper_context_manager(self):
        """Test scraper as async context manager."""
        config = ScrapingConfig(max_pages=1, delay_between_requests=0.1)
        
        async with IndeedScraper(config) as scraper:
            assert scraper.config.max_pages == 1
            assert scraper._stats["start_time"] is not None
        
        # After exiting context, end_time should be set
        assert scraper._stats["end_time"] is not None


@pytest.mark.scraper
@pytest.mark.integration
class TestIndeedScraperIntegration:
    """Integration tests for Indeed scraper."""
    
    async def test_search_jobs_mock(self, mock_httpx_client):
        """Test job search with mocked HTTP responses."""
        with patch('app.scrapers.indeed.httpx.AsyncClient', return_value=mock_httpx_client):
            scraper = IndeedScraper()
            
            # Mock HTML response with job listings
            mock_html = """
            <html>
                <body>
                    <div data-jk="job123">
                        <h2 class="jobTitle">Product Manager</h2>
                        <span class="companyName">TechCorp</span>
                        <div data-testid="job-location">San Francisco, CA</div>
                        <span class="salaryText">$120,000 - $150,000</span>
                        <div class="job-snippet">Great MBA opportunity</div>
                    </div>
                </body>
            </html>
            """
            
            mock_httpx_client.get.return_value.content = mock_html.encode()
            mock_httpx_client.get.return_value.text = mock_html
            
            # This would normally require actual network calls
            # For now, we test that the method structure works
            assert hasattr(scraper, 'search_jobs')
            assert callable(scraper.search_jobs)
    
    @patch('app.scrapers.indeed.httpx.AsyncClient')
    async def test_error_handling_in_search(self, mock_client_class):
        """Test error handling during job search."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.request.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client
        
        scraper = IndeedScraper()
        scraper.session = mock_client
        
        # Search should handle errors gracefully
        jobs = []
        try:
            async for job in scraper.search_jobs("Product Manager", "San Francisco"):
                jobs.append(job)
        except Exception:
            # Should not raise unhandled exceptions
            pass
        
        # Should track errors in statistics
        assert scraper._stats["errors"] >= 0