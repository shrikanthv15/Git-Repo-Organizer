FROM python:3.12-slim AS base

# Install system dependencies (git needed for deep repo scanning)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Cache dependency installation — use requirements.txt so adding new
# packages does not require regenerating uv.lock locally first.
COPY pyproject.toml requirements.txt ./
COPY uv.lock* ./
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
