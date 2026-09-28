FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --no-cache-dir -e .
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
