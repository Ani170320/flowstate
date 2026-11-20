import sys
import os
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


@pytest_asyncio.fixture(loop_scope="function")
async def async_client():
    """Async HTTP test client for FLOWSTATE API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
