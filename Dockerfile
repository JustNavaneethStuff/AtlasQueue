FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 atlas \
    && useradd --uid 10001 --gid atlas --create-home atlas

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --upgrade pip && pip install .

FROM base AS api
EXPOSE 8000
USER atlas
CMD ["atlasqueue-api"]

FROM base AS worker
USER atlas
CMD ["atlasqueue-worker"]

FROM base AS scheduler
USER atlas
CMD ["atlasqueue-scheduler"]
