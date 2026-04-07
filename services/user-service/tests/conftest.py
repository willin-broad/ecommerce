"""
Test configuration for user-service.

Key design decisions:
- Uses SQLite in-memory for speed (no real PostgreSQL needed)
- `StaticPool` forces ALL connections to share ONE underlying SQLite connection,
  so tables created by the fixture are visible to every session in the test.
- `src.database.engine` and `src.database.SessionLocal` are patched BEFORE the
  app module is imported, so the lifespan's `create_all` also targets SQLite.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --- Patch the DB engine BEFORE importing the app --------------------------
# This ensures main.py's lifespan `create_all` targets SQLite, not PostgreSQL.
import src.database as _db

SQLITE_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # Single shared connection → same in-memory DB everywhere
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

_db.engine = _test_engine
_db.SessionLocal = _TestingSession
# ---------------------------------------------------------------------------

from src.main import app           # noqa: E402 — must be imported after DB patch
from src.database import Base, get_db  # noqa: E402


def _override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    """Create all tables before each test, drop them after — full isolation."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def client():
    """TestClient backed by the patched in-memory SQLite DB."""
    return TestClient(app)
