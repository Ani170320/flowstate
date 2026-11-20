"""
Database dependencies for FastAPI route handlers.
"""

from app.database.connection import get_db

__all__ = ["get_db"]
