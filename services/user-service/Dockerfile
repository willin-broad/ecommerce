FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
ENV PATH=/root/.local/bin:$PATH
EXPOSE 3001
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3001"]
