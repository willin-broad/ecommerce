import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .database import Base, engine
from .routers import auth, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - Startup:  Creates all database tables (idempotent via CREATE TABLE IF NOT EXISTS).
    - Shutdown: Logs graceful shutdown message.

    Note: In production, Alembic migrations handle schema changes.
    create_all() here acts as a safety net for fresh environments.
    """
    logger.info("Starting user-service — initialising database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down user-service.")


app = FastAPI(
    title="User Service",
    version="1.0.0",
    description="Authentication & user management microservice for the eCommerce platform.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Prometheus metrics — exposes /metrics endpoint automatically
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health", tags=["observability"])
def health():
    """Health check endpoint — used by Docker/Kubernetes liveness probes."""
    return {"status": "ok", "service": "user-service"}
