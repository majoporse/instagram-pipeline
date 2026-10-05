# syntax=docker/dockerfile:1

# Official uv image: uv + Python 3.13 on Debian 13 (trixie).
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.25-python3.13-trixie-slim

FROM ${UV_IMAGE} AS builder

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM ${UV_IMAGE}

ENV PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY --from=builder /opt/venv /opt/venv

COPY --from=builder /app /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install --with-deps --only-shell chromium \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app /ms-playwright

WORKDIR /app
USER app

EXPOSE 8000

CMD ["uvicorn", "instagram_pipeline.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
