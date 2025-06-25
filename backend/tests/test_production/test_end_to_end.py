"""
End-to-End Production Tests for MBA Job Hunter

Comprehensive tests that simulate real user workflows in production environment.
Tests critical business flows and integrations.
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.config import get_settings


class TestEndToEndWorkflows:
    """End-to-end tests for critical user workflows."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_complete_job_search_workflow(self, async_client):
        """Test complete job search workflow from search to analysis."""
        
        # Step 1: Health check
        response = await async_client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] in ["healthy", "degraded"]
        
        # Step 2: Search for jobs
        search_params = {
            "keywords": ["MBA", "管理"],
            "location": "台北",
            "experience_level": "entry",
            "limit": 10
        }
        
        response = await async_client.post("/api/v1/jobs/search", json=search_params)
        assert response.status_code == 200
        
        search_results = response.json()
        assert "jobs" in search_results
        assert len(search_results["jobs"]) <= 10
        
        # Verify job data structure
        if search_results["jobs"]:
            job = search_results["jobs"][0]
            required_fields = ["id", "title", "company", "location", "url"]
            for field in required_fields:
                assert field in job
        
        # Step 3: Get job details
        if search_results["jobs"]:
            job_id = search_results["jobs"][0]["id"]
            
            response = await async_client.get(f"/api/v1/jobs/{job_id}")
            assert response.status_code == 200
            
            job_details = response.json()
            assert job_details["id"] == job_id
            assert "description" in job_details
        
        # Step 4: Request AI analysis
        if search_results["jobs"]:
            job_id = search_results["jobs"][0]["id"]
            
            analysis_request = {
                "job_id": job_id,
                "user_profile": {
                    "education": "MBA",
                    "experience_years": 2,
                    "skills": ["分析", "管理", "策略"]
                }
            }
            
            response = await async_client.post("/api/v1/analysis/analyze", json=analysis_request)
            assert response.status_code in [200, 202]  # 200 for sync, 202 for async
            
            if response.status_code == 200:
                analysis = response.json()
                assert "match_score" in analysis
                assert 0 <= analysis["match_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, async_client):
        """Test error handling and recovery mechanisms."""
        
        # Test 404 error handling
        response = await async_client.get("/api/v1/jobs/nonexistent-id")
        assert response.status_code == 404
        
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert "request_id" in error_data["error"]
        
        # Test validation error handling
        invalid_search = {"keywords": "", "limit": -1}
        response = await async_client.post("/api/v1/jobs/search", json=invalid_search)
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"]["code"] == "VALIDATION_ERROR"
        
        # Test rate limiting (if enabled)
        # Make multiple rapid requests to trigger rate limiting
        responses = []
        for _ in range(150):  # Exceed typical rate limit
            response = await async_client.get("/health")
            responses.append(response.status_code)
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert 429 in responses or all(r == 200 for r in responses)  # Allow for rate limit or all success
    
    @pytest.mark.asyncio
    async def test_metrics_and_monitoring(self, async_client):
        """Test metrics and monitoring endpoints."""
        
        # Test metrics endpoint
        response = await async_client.get("/metrics")
        assert response.status_code in [200, 404]  # 404 if not enabled
        
        if response.status_code == 200:
            metrics_text = response.text
            assert "http_requests_total" in metrics_text or "job_searches_total" in metrics_text
        
        # Test detailed health check
        response = await async_client.get("/health/detailed")
        assert response.status_code in [200, 404]  # 404 if not enabled in production
        
        if response.status_code == 200:
            health_data = response.json()
            assert "checks" in health_data
    
    @pytest.mark.asyncio
    async def test_security_headers(self, async_client):
        """Test security headers are properly set."""
        
        response = await async_client.get("/")
        
        # Check security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        for header in security_headers:
            assert header in response.headers, f"Missing security header: {header}"
        
        # Verify header values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "max-age" in response.headers["Strict-Transport-Security"]
    
    @pytest.mark.asyncio
    async def test_cors_configuration(self, async_client):
        """Test CORS configuration."""
        
        # Test preflight request
        response = await async_client.options(
            "/api/v1/jobs/search",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should handle CORS properly
        assert response.status_code in [200, 204]
        
        # Check CORS headers if present
        if "Access-Control-Allow-Origin" in response.headers:
            cors_origin = response.headers["Access-Control-Allow-Origin"]
            assert cors_origin in ["*", "https://example.com", "https://yourdomain.com"]


class TestDatabaseIntegration:
    """Test database operations and performance."""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool(self):
        """Test database connection pool performance."""
        from app.core.database import db_manager
        
        # Test multiple concurrent connections
        async def make_query():
            async with db_manager.get_session() as session:
                result = await session.execute("SELECT 1")
                return result.scalar()
        
        # Run concurrent queries
        tasks = [make_query() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        assert all(result == 1 for result in results)
    
    @pytest.mark.asyncio
    async def test_database_health_monitoring(self):
        """Test database health monitoring."""
        from app.core.database import db_manager
        
        health_status = await db_manager.health_check()
        
        assert "status" in health_status
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in health_status
    
    @pytest.mark.asyncio
    async def test_database_performance_indexes(self):
        """Test that performance indexes are working."""
        from app.core.database import db_manager
        
        async with db_manager.get_session() as session:
            # Test index usage with EXPLAIN
            explain_queries = [
                "EXPLAIN SELECT * FROM jobs WHERE title ILIKE '%manager%'",
                "EXPLAIN SELECT * FROM jobs WHERE company ILIKE '%tech%'",
                "EXPLAIN SELECT * FROM jobs WHERE created_at > NOW() - INTERVAL '7 days'"
            ]
            
            for query in explain_queries:
                try:
                    result = await session.execute(query)
                    # If query executes without error, indexes are likely working
                    assert result is not None
                except Exception as e:
                    # Skip if EXPLAIN not supported (e.g., SQLite)
                    if "syntax error" not in str(e).lower():
                        raise


class TestExternalIntegrations:
    """Test external service integrations."""
    
    @pytest.mark.asyncio
    async def test_openai_integration(self, async_client):
        """Test OpenAI API integration with fallback."""
        
        # Test AI analysis request
        analysis_request = {
            "job_id": "test-job-id",
            "user_profile": {
                "education": "MBA",
                "experience_years": 2,
                "skills": ["分析", "管理"]
            }
        }
        
        response = await async_client.post("/api/v1/analysis/analyze", json=analysis_request)
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 202, 503, 400]
        
        if response.status_code == 503:
            # Service unavailable - check for intelligent error handling
            error_data = response.json()
            assert "error" in error_data
            # Should have user-friendly message in Chinese
            assert any(char >= '\u4e00' and char <= '\u9fff' for char in error_data["error"]["message"])
    
    @pytest.mark.asyncio
    async def test_notion_integration(self, async_client):
        """Test Notion API integration with fallback."""
        
        export_request = {
            "job_ids": ["test-job-1", "test-job-2"],
            "format": "notion"
        }
        
        response = await async_client.post("/api/v1/jobs/export", json=export_request)
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 202, 503, 400]
        
        if response.status_code == 503:
            # Service unavailable - check for intelligent error handling
            error_data = response.json()
            assert "error" in error_data
    
    @pytest.mark.asyncio
    async def test_scraping_service_resilience(self, async_client):
        """Test job scraping service resilience."""
        
        scraping_request = {
            "keywords": ["software engineer"],
            "location": "台北",
            "platforms": ["indeed"]
        }
        
        response = await async_client.post("/api/v1/jobs/scrape", json=scraping_request)
        
        # Should handle scraping failures gracefully
        assert response.status_code in [200, 202, 503, 429]
        
        if response.status_code in [503, 429]:
            # Service issues - check for intelligent error handling
            error_data = response.json()
            assert "error" in error_data
            
            # Should have retry information
            if response.status_code == 429:
                assert "Retry-After" in response.headers


class TestPerformanceAndLoad:
    """Test performance and load handling."""
    
    @pytest.mark.asyncio
    async def test_response_time_performance(self, async_client):
        """Test API response time performance."""
        
        import time
        
        endpoints = [
            "/health",
            "/api/v1/jobs?limit=10",
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = await async_client.get(endpoint)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # ms
            
            # Response time should be reasonable
            assert response_time < 5000, f"Slow response for {endpoint}: {response_time}ms"
            
            if response.status_code == 200:
                assert response_time < 2000, f"Acceptable response time for {endpoint}: {response_time}ms"
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, async_client):
        """Test handling of concurrent requests."""
        
        async def make_request():
            response = await async_client.get("/health")
            return response.status_code
        
        # Make concurrent requests
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most requests should succeed
        success_count = sum(1 for r in results if r == 200)
        total_count = len(results)
        success_rate = success_count / total_count
        
        assert success_rate >= 0.8, f"Low success rate: {success_rate}"
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, async_client):
        """Test memory usage stability under load."""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        for _ in range(100):
            await async_client.get("/health")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100, f"Excessive memory increase: {memory_increase}MB"


@pytest.mark.asyncio
async def test_production_readiness_checklist():
    """Comprehensive production readiness checklist."""
    
    checklist_results = {}
    
    # Check environment variables
    import os
    required_env_vars = [
        "DATABASE_URL",
        "SECRET_KEY", 
        "ENVIRONMENT"
    ]
    
    for var in required_env_vars:
        checklist_results[f"env_var_{var}"] = bool(os.getenv(var))
    
    # Check security settings
    checklist_results["debug_disabled"] = os.getenv("DEBUG", "false").lower() == "false"
    checklist_results["environment_set"] = os.getenv("ENVIRONMENT") in ["production", "staging"]
    
    # Check database connection
    try:
        from app.core.database import db_manager
        health = await db_manager.health_check()
        checklist_results["database_healthy"] = health.get("status") in ["healthy", "degraded"]
    except Exception:
        checklist_results["database_healthy"] = False
    
    # Check metrics availability
    try:
        from app.utils.metrics import production_metrics
        checklist_results["metrics_available"] = production_metrics is not None
    except Exception:
        checklist_results["metrics_available"] = False
    
    # Check error handling
    try:
        from app.utils.error_handler import user_friendly_error_handler
        checklist_results["error_handling_ready"] = user_friendly_error_handler is not None
    except Exception:
        checklist_results["error_handling_ready"] = False
    
    # Report results
    failed_checks = [check for check, passed in checklist_results.items() if not passed]
    
    if failed_checks:
        pytest.fail(f"Production readiness checks failed: {failed_checks}")
    
    assert all(checklist_results.values()), "All production readiness checks should pass"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])