"""
Basic Tests for MBA Job Hunter

Simple test cases for core functionality.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_jobs_endpoint():
    """Test jobs listing endpoint."""
    response = client.get("/api/v1/jobs/")
    assert response.status_code in [200, 401]  # May require auth


def test_jobs_search():
    """Test job search functionality."""
    response = client.get("/api/v1/jobs/search?query=engineer")
    assert response.status_code in [200, 401]  # May require auth


def test_analysis_endpoint():
    """Test analysis endpoint."""
    response = client.get("/api/v1/analysis/")
    assert response.status_code in [200, 401]  # May require auth