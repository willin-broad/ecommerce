# User Service

Authentication & user management microservice for the eCommerce platform. This service handles user registration, authentication, authorization, and profile management.

## Tech Stack
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL (via SQLAlchemy & Alembic)
- **Authentication**: JWT & bcrypt

## Quick Start (Local)

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   ```

3. Run the application:
   ```bash
   uvicorn src.main:app --reload --port 3001
   ```

## Docker

Build and run with docker compose via the root directory:
```bash
cd ../../
docker compose up --build
```

## Testing

Run tests with `pytest`:
```bash
pytest
```
