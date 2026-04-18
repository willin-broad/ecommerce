"""
Test configuration for user-service.

Key design decisions:
- RATELIMIT_ENABLED=false must be set before ANY src import so the limiter
  module reads it at import time and creates a disabled Limiter instance.
- Uses SQLite in-memory for speed (no real PostgreSQL needed).
- `StaticPool` forces ALL connections to share ONE underlying SQLite connection,
  so tables created by the fixture are visible to every session in the test.
- `src.database.engine` and `src.database.SessionLocal` are patched BEFORE the
  app module is imported, so the lifespan's `create_all` also targets SQLite.
- The rate limiter's in-memory storage is reset between every test to prevent
  counts from accumulating across the 40+ test suite.
"""

import os

# Disable rate limiting for tests — MUST be before any src imports
os.environ["RATELIMIT_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

# --- Patch the DB engine BEFORE importing the app --------------------------
import src.database as _db  # noqa: E402

SQLITE_URL = "sqlite:///:memory:"

# Public names — imported directly in test files
test_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # Single shared connection → same in-memory DB everywhere
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

_db.engine = test_engine
_db.SessionLocal = TestingSessionLocal
# ---------------------------------------------------------------------------

from src.main import app           # noqa: E402 — must be imported after DB patch
from src.database import Base, get_db  # noqa: E402
from src.limiter import limiter as _limiter  # noqa: E402

# Force-disable the limiter on the shared instance — this affects all already-
# decorated routes because the decorator captures the limiter object by reference.
_limiter._enabled = False


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    """Create all tables before each test, drop them after — full isolation."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """
    Clear slowapi's in-memory rate limit counters between tests.
    Without this, counts accumulate across the 40+ test suite and
    eventually trigger 429s on endpoints like /register (10/minute).
    The storage is cleared AFTER each test so the next test starts clean.
    """
    yield
    if hasattr(_limiter, "_storage") and _limiter._storage is not None:
        try:
            _limiter._storage.reset()
        except Exception:
            pass  # Storage type may not support reset — safe to ignore


@pytest.fixture()
def client():
    """TestClient backed by the patched in-memory SQLite DB."""
    return TestClient(app)
