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
COPY --chown=appuser:appuser pyproject.toml ./

ENV PYTHONPATH=/app/src

USER appuser

CMD ["python", "-m", "hub_bot"]
