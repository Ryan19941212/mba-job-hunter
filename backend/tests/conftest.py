"""
Simple Test Configuration for MBA Job Hunter

Basic test setup and fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for API endpoints."""
    return TestClient(app)