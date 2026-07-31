# The Hub Bot — Production Dockerfile
# Polling-based Telegram bot without HTTP server

FROM python:3.14-slim AS builder

# Install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /build

# Copy dependency files only (for layer caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies to a specific location
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --only main --no-root


# Runtime stage
FROM python:3.14-slim

# Create non-root user
RUN useradd --create-home --no-log-init appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser pyproject.toml ./

ENV PYTHONPATH=/app/src

USER appuser

# Diagnostics and startup
CMD ["sh", "-c", "set -e; \
  echo 'DATABASE_URL check:'; \
  test -n \"$DATABASE_URL\" || (echo 'ERROR: DATABASE_URL not set'; exit 1); \
  echo \"✓ DATABASE_URL is configured\"; \
  echo ''; \
  echo 'Running Alembic migrations...'; \
  alembic upgrade head && \
  echo ''; \
  echo 'Starting bot...'; \
  python -m hub_bot"]
