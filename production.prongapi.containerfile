FROM python:3.13-slim as build-stage

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev gdal-bin proj-bin ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN uv init --bare

COPY ./airial_api .
RUN uv sync --frozen --no-dev

FROM python:3.13-slim as production-stage


COPY --from=build-stage /app/.venv /app/.venv
COPY --from=build-stage /app /app

CMD ["gunicorn", "-c", "gunicorn.py", "app:create_app()"]
