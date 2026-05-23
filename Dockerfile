# Stage 1: Build
FROM python:3.11-alpine3.21@sha256:cc89153ee2e125296614f6a032cb473e2bc2c0203cbe2305c917ece8866e5b01 AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime
FROM python:3.11-alpine3.21@sha256:cc89153ee2e125296614f6a032cb473e2bc2c0203cbe2305c917ece8866e5b01

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup src/ ./src/

RUN mkdir -p /app/data && chown appuser:appgroup /app/data

USER appuser

ENV DML_DB_PATH=/app/data/decisions.db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

CMD ["uvicorn", "decision_memory.api:app", "--host", "0.0.0.0", "--port", "8000"]
