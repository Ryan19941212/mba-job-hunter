"""
Test Suite

Comprehensive test framework for the MBA Job Hunter application
including unit tests, integration tests, and end-to-end tests.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
import sys
import os

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Test configuration
pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.auth",
    "tests.fixtures.services",
    "tests.fixtures.data"
]


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (slower)"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests (slowest)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as requiring asyncio"
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()