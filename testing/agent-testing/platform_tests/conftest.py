"""Session-level fixtures for platform map coverage tests."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from transport.pool import close_sessions


@pytest.fixture(autouse=True, scope="session")
def cleanup_transport_sessions():
    """Clean up transport resources after all platform coverage tests complete."""
    yield
    asyncio.run(close_sessions())
