import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .database import Base, engine
from .limiter import limiter
from .routers import auth, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - Startup:  Creates all database tables (idempotent).
    - Shutdown: Logs graceful shutdown.

    Note: Alembic handles schema changes in production.
    create_all() is a safety net for fresh environments.
    """
    logger.info("Starting user-service — initialising database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down user-service.")


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a clean 429 JSON response instead of slowapi's plain-text default."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}. Please try again later."},
    )


app = FastAPI(
    title="User Service",
    version="1.0.0",
    description="Authentication & user management microservice for the eCommerce platform.",
    lifespan=lifespan,
    # Swagger/ReDoc disabled in production — leaks full API surface to scanners
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
)

# Wire up rate limiter — routes read app.state.limiter via slowapi internals
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# Prometheus metrics — exposes /metrics endpoint automatically
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health", tags=["observability"])
def health():
    """Health check endpoint — used by Docker/Kubernetes liveness probes."""
    return {"status": "ok", "service": "user-service"}
