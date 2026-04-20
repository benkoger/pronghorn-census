FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev gdal-bin proj-bin ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH="/app"

WORKDIR /app

COPY ./airial_api/pyproject.toml ./airial_api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY ./airial_api .

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8000", "--debug"]