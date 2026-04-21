FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
# Install to a fixed prefix so we can copy cleanly into the final image
RUN pip install --no-cache-dir -r requirements.txt --prefix=/install

FROM python:3.11-slim
WORKDIR /app

# Non-root user — reduces blast radius if a dependency has a vulnerability
RUN useradd --no-create-home --no-log-init -r -u 1001 appuser

# Copy installed packages from builder (already in /usr/local PATH hierarchy)
COPY --from=builder /install /usr/local

COPY --chown=appuser src ./src
COPY --chown=appuser alembic.ini ./alembic.ini
COPY --chown=appuser alembic ./alembic

USER appuser
EXPOSE 3001
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3001"]
