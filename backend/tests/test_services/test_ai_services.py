"""
Tests for AI services.

Tests OpenAI and Anthropic integrations for job analysis,
fitting scoring, and text processing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.ai_services import (
    OpenAIService,
    AnthropicService,
    JobAnalyzer,
    AIServiceError,
    JobFitScorer
)


@pytest.mark.ai
@pytest.mark.unit
class TestOpenAIService:
    """Test OpenAI service functionality."""
    
    def test_openai_initialization(self):
        """Test OpenAI service initialization."""
        service = OpenAIService(api_key="test_key", model="gpt-4")
        
        assert service.api_key == "test_key"
        assert service.model == "gpt-4"
        assert service.client is not None
    
    def test_openai_initialization_no_key(self):
        """Test OpenAI service initialization without API key."""
        with patch('app.services.ai_services.get_settings') as mock_settings:
            mock_settings.return_value.OPENAI_API_KEY = None
            
            with pytest.raises(AIServiceError, match="OpenAI API key"):
                OpenAIService()
    
    @patch('app.services.ai_services.AsyncOpenAI')
    async def test_analyze_job_description(self, mock_openai_class):
        """Test job description analysis."""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{"score": 85, "reasoning": "High MBA relevance", "skills": ["Strategy", "Leadership"]}'''
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        service = OpenAIService(api_key="test_key")
        service.client = mock_client
        
        result = await service.analyze_job_description(
            "Product Manager role requiring MBA",
            "Looking for MBA graduate with strategy background"
        )
        
        assert result["score"] == 85
        assert "reasoning" in result
        assert "skills" in result
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('app.services.ai_services.AsyncOpenAI')
    async def test_analyze_job_api_error(self, mock_openai_class):
        """Test handling of OpenAI API errors."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        service = OpenAIService(api_key="test_key")
        service.client = mock_client
        
        with pytest.raises(AIServiceError):
            await service.analyze_job_description("Title", "Description")
    
    @patch('app.services.ai_services.AsyncOpenAI')
    async def test_analyze_job_invalid_json(self, mock_openai_class):
        """Test handling of invalid JSON response."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        service = OpenAIService(api_key="test_key")
        service.client = mock_client
        
        with pytest.raises(AIServiceError, match="Invalid JSON"):
            await service.analyze_job_description("Title", "Description")
    
    @patch('app.services.ai_services.AsyncOpenAI')
    async def test_extract_skills(self, mock_openai_class):
        """Test skills extraction from job description."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["Python", "SQL", "MBA", "Leadership"]'
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        service = OpenAIService(api_key="test_key")
        service.client = mock_client
        
        skills = await service.extract_skills(
            "Product Manager with Python and SQL experience"
        )
        
        assert len(skills) == 4
        assert "Python" in skills
        assert "MBA" in skills
    
    async def test_context_manager(self):
        """Test OpenAI service as async context manager."""
        async with OpenAIService(api_key="test_key") as service:
            assert service.api_key == "test_key"
            assert service.client is not None


@pytest.mark.ai
@pytest.mark.unit
class TestAnthropicService:
    """Test Anthropic service functionality."""
    
    def test_anthropic_initialization(self):
        """Test Anthropic service initialization."""
        service = AnthropicService(api_key="test_key", model="claude-3-sonnet")
        
        assert service.api_key == "test_key"
        assert service.model == "claude-3-sonnet"
        assert service.client is not None
    
    def test_anthropic_initialization_no_key(self):
        """Test Anthropic service initialization without API key."""
        with patch('app.services.ai_services.get_settings') as mock_settings:
            mock_settings.return_value.ANTHROPIC_API_KEY = None
            
            with pytest.raises(AIServiceError, match="Anthropic API key"):
                AnthropicService()
    
    @patch('app.services.ai_services.AsyncAnthropic')
    async def test_analyze_job_description(self, mock_anthropic_class):
        """Test job description analysis with Anthropic."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '''{"score": 90, "reasoning": "Excellent MBA fit", "skills": ["Strategy", "Consulting"]}'''
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        service = AnthropicService(api_key="test_key")
        service.client = mock_client
        
        result = await service.analyze_job_description(
            "Strategy Consultant",
            "MBA required, consulting background preferred"
        )
        
        assert result["score"] == 90
        assert "reasoning" in result
        assert "skills" in result
        mock_client.messages.create.assert_called_once()
    
    @patch('app.services.ai_services.AsyncAnthropic')
    async def test_generate_job_summary(self, mock_anthropic_class):
        """Test job summary generation."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Excellent opportunity for MBA graduates in strategy consulting."
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        service = AnthropicService(api_key="test_key")
        service.client = mock_client
        
        summary = await service.generate_job_summary(
            "Strategy Consultant at Top Firm",
            "Long job description..."
        )
        
        assert "MBA graduates" in summary
        assert "strategy consulting" in summary


@pytest.mark.ai
@pytest.mark.unit
class TestJobAnalyzer:
    """Test JobAnalyzer functionality."""
    
    def test_job_analyzer_initialization(self, mock_openai_service, mock_anthropic_service):
        """Test JobAnalyzer initialization."""
        analyzer = JobAnalyzer(
            openai_service=mock_openai_service,
            anthropic_service=mock_anthropic_service
        )
        
        assert analyzer.openai_service == mock_openai_service
        assert analyzer.anthropic_service == mock_anthropic_service
        assert analyzer.preferred_service == "openai"
    
    async def test_analyze_job_with_openai(self, mock_openai_service):
        """Test job analysis using OpenAI."""
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "High MBA relevance",
            "skills": ["Strategy", "Leadership"]
        }
        
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        
        result = await analyzer.analyze_job(
            "Product Manager",
            "Looking for MBA graduate",
            service="openai"
        )
        
        assert result["score"] == 85
        assert result["service_used"] == "openai"
        mock_openai_service.analyze_job_description.assert_called_once()
    
    async def test_analyze_job_with_anthropic(self, mock_anthropic_service):
        """Test job analysis using Anthropic."""
        mock_anthropic_service.analyze_job_description.return_value = {
            "score": 90,
            "reasoning": "Perfect MBA fit",
            "skills": ["Consulting", "Strategy"]
        }
        
        analyzer = JobAnalyzer(anthropic_service=mock_anthropic_service)
        
        result = await analyzer.analyze_job(
            "Management Consultant",
            "MBA required",
            service="anthropic"
        )
        
        assert result["score"] == 90
        assert result["service_used"] == "anthropic"
        mock_anthropic_service.analyze_job_description.assert_called_once()
    
    async def test_analyze_job_fallback(self, mock_openai_service, mock_anthropic_service):
        """Test fallback between AI services."""
        mock_openai_service.analyze_job_description.side_effect = AIServiceError("OpenAI failed")
        mock_anthropic_service.analyze_job_description.return_value = {
            "score": 80,
            "reasoning": "Good MBA fit",
            "skills": ["Analysis"]
        }
        
        analyzer = JobAnalyzer(
            openai_service=mock_openai_service,
            anthropic_service=mock_anthropic_service
        )
        
        result = await analyzer.analyze_job(
            "Business Analyst",
            "MBA preferred"
        )
        
        assert result["score"] == 80
        assert result["service_used"] == "anthropic"
        mock_openai_service.analyze_job_description.assert_called_once()
        mock_anthropic_service.analyze_job_description.assert_called_once()
    
    async def test_analyze_job_both_fail(self, mock_openai_service, mock_anthropic_service):
        """Test when both AI services fail."""
        mock_openai_service.analyze_job_description.side_effect = AIServiceError("OpenAI failed")
        mock_anthropic_service.analyze_job_description.side_effect = AIServiceError("Anthropic failed")
        
        analyzer = JobAnalyzer(
            openai_service=mock_openai_service,
            anthropic_service=mock_anthropic_service
        )
        
        with pytest.raises(AIServiceError, match="All AI services failed"):
            await analyzer.analyze_job("Test Job", "Test description")
    
    async def test_extract_skills_combined(self, mock_openai_service, mock_anthropic_service):
        """Test skills extraction combining both services."""
        mock_openai_service.extract_skills.return_value = ["Python", "SQL", "MBA"]
        mock_anthropic_service.extract_skills.return_value = ["Leadership", "Strategy", "MBA"]
        
        analyzer = JobAnalyzer(
            openai_service=mock_openai_service,
            anthropic_service=mock_anthropic_service
        )
        
        skills = await analyzer.extract_skills_combined(
            "Product Manager with Python, SQL, and MBA background"
        )
        
        # Should combine and deduplicate skills
        assert "Python" in skills
        assert "SQL" in skills
        assert "MBA" in skills
        assert "Leadership" in skills
        assert "Strategy" in skills
        assert len([s for s in skills if s == "MBA"]) == 1  # Deduplicated
    
    async def test_batch_analyze_jobs(self, mock_openai_service, sample_job_list):
        """Test batch job analysis."""
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "Good fit",
            "skills": ["Strategy"]
        }
        
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        
        results = await analyzer.batch_analyze_jobs(sample_job_list)
        
        assert len(results) == len(sample_job_list)
        for result in results:
            assert result["score"] == 85
            assert result["service_used"] == "openai"
    
    async def test_context_manager(self, mock_openai_service):
        """Test JobAnalyzer as async context manager."""
        async with JobAnalyzer(openai_service=mock_openai_service) as analyzer:
            assert analyzer.openai_service == mock_openai_service


@pytest.mark.ai
@pytest.mark.unit
class TestJobFitScorer:
    """Test JobFitScorer functionality."""
    
    def test_scorer_initialization(self):
        """Test JobFitScorer initialization."""
        scorer = JobFitScorer()
        
        assert scorer.mba_keywords is not None
        assert len(scorer.mba_keywords) > 0
        assert scorer.weight_config is not None
    
    def test_calculate_keyword_score(self):
        """Test keyword-based scoring."""
        scorer = JobFitScorer()
        
        # High MBA relevance text
        high_score_text = "MBA required, strategy consulting, leadership role, business development"
        high_score = scorer._calculate_keyword_score(high_score_text)
        
        # Low MBA relevance text
        low_score_text = "Manual labor, warehouse work, physical tasks"
        low_score = scorer._calculate_keyword_score(low_score_text)
        
        assert high_score > low_score
        assert high_score > 0.5
        assert low_score < 0.3
    
    def test_calculate_title_score(self):
        """Test title-based scoring."""
        scorer = JobFitScorer()
        
        # MBA-relevant titles
        high_titles = [
            "Product Manager",
            "Strategy Consultant",
            "Business Analyst",
            "Management Consultant"
        ]
        
        # Non-MBA titles
        low_titles = [
            "Warehouse Worker",
            "Truck Driver",
            "Cashier",
            "Construction Worker"
        ]
        
        for title in high_titles:
            score = scorer._calculate_title_score(title)
            assert score > 0.6
        
        for title in low_titles:
            score = scorer._calculate_title_score(title)
            assert score < 0.4
    
    def test_calculate_company_score(self):
        """Test company-based scoring."""
        scorer = JobFitScorer()
        
        # Top consulting/tech companies
        high_companies = [
            "McKinsey & Company",
            "Boston Consulting Group",
            "Google",
            "Microsoft"
        ]
        
        # Less MBA-focused companies
        low_companies = [
            "Local Restaurant",
            "Small Factory",
            "Unknown Startup"
        ]
        
        for company in high_companies:
            score = scorer._calculate_company_score(company)
            assert score > 0.5
        
        for company in low_companies:
            score = scorer._calculate_company_score(company)
            assert score <= 0.5
    
    def test_calculate_requirements_score(self):
        """Test requirements-based scoring."""
        scorer = JobFitScorer()
        
        # MBA-focused requirements
        high_req = "MBA required, 3+ years consulting experience, strategy background"
        high_score = scorer._calculate_requirements_score(high_req)
        
        # Non-MBA requirements
        low_req = "High school diploma, physical fitness, driver's license"
        low_score = scorer._calculate_requirements_score(low_req)
        
        assert high_score > low_score
        assert high_score > 0.7
        assert low_score < 0.3
    
    async def test_calculate_fit_score(self, sample_job_data):
        """Test complete fit score calculation."""
        scorer = JobFitScorer()
        
        # Create MBA-relevant job
        mba_job = sample_job_data.copy()
        mba_job["title"] = "Product Manager"
        mba_job["company_name"] = "Google"
        mba_job["description"] = "Looking for MBA graduate with strategy experience"
        mba_job["requirements"] = "MBA required, consulting background preferred"
        
        score = await scorer.calculate_fit_score(mba_job)
        
        assert 0 <= score <= 100
        assert score > 70  # Should be high for MBA-relevant job
    
    async def test_calculate_fit_score_low_relevance(self):
        """Test fit score for low-relevance job."""
        scorer = JobFitScorer()
        
        low_relevance_job = {
            "title": "Warehouse Worker",
            "company_name": "Unknown Logistics",
            "description": "Physical labor, loading and unloading trucks",
            "requirements": "High school diploma, physical fitness"
        }
        
        score = await scorer.calculate_fit_score(low_relevance_job)
        
        assert 0 <= score <= 100
        assert score < 30  # Should be low for non-MBA job
    
    def test_weight_config_customization(self):
        """Test custom weight configuration."""
        custom_weights = {
            "title": 0.5,
            "description": 0.3,
            "company": 0.1,
            "requirements": 0.1
        }
        
        scorer = JobFitScorer(weight_config=custom_weights)
        
        assert scorer.weight_config == custom_weights
        assert sum(scorer.weight_config.values()) == 1.0


@pytest.mark.ai
@pytest.mark.integration
class TestAIServicesIntegration:
    """Integration tests for AI services."""
    
    async def test_full_job_analysis_workflow(self, mock_openai_service, sample_job_data):
        """Test complete job analysis workflow."""
        # Mock AI service responses
        mock_openai_service.analyze_job_description.return_value = {
            "score": 85,
            "reasoning": "Strong MBA relevance due to strategy focus",
            "skills": ["Strategy", "Leadership", "MBA", "Consulting"]
        }
        mock_openai_service.extract_skills.return_value = [
            "Python", "SQL", "MBA", "Strategy", "Leadership"
        ]
        
        # Initialize services
        analyzer = JobAnalyzer(openai_service=mock_openai_service)
        scorer = JobFitScorer()
        
        # Run analysis
        ai_result = await analyzer.analyze_job(
            sample_job_data["title"],
            sample_job_data["description"]
        )
        
        fit_score = await scorer.calculate_fit_score(sample_job_data)
        
        skills = await analyzer.extract_skills_combined(
            sample_job_data["description"]
        )
        
        # Verify results
        assert ai_result["score"] == 85
        assert "reasoning" in ai_result
        assert len(ai_result["skills"]) > 0
        
        assert 0 <= fit_score <= 100
        assert len(skills) > 0
        assert "MBA" in skills
    
    async def test_error_handling_workflow(self, mock_openai_service, mock_anthropic_service):
        """Test error handling across AI services."""
        # Setup failures
        mock_openai_service.analyze_job_description.side_effect = AIServiceError("OpenAI failed")
        mock_anthropic_service.analyze_job_description.side_effect = AIServiceError("Anthropic failed")
        
        analyzer = JobAnalyzer(
            openai_service=mock_openai_service,
            anthropic_service=mock_anthropic_service
        )
        
        # Should raise error when all services fail
        with pytest.raises(AIServiceError):
            await analyzer.analyze_job("Test Job", "Test description")
        
        # Scorer should still work independently
        scorer = JobFitScorer()
        score = await scorer.calculate_fit_score({
            "title": "Product Manager",
            "company_name": "Google",
            "description": "MBA role",
            "requirements": "MBA required"
        })
        
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
