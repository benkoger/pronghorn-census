FROM python:3.13-slim-bookworm as build-stage

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libpq-dev \
    bash \
    python3-venv \
    gcc \
    build-essential \
    libsqlite3-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /venv

COPY ./requirements.txt requirements.txt

COPY ./crop_generator /venv/crop_generator

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

RUN /bin/bash -c "uv venv api_env && source api_env/bin/activate && uv pip install --no-cache-dir -r requirements.txt"

FROM python:3.13-slim as production-stage

COPY --from=build-stage /venv/api_env /venv/api_env

COPY --from=build-stage /venv/crop_generator /venv/crop_generator

ENV PATH="/venv/api_env/bin:$PATH"

WORKDIR /app

COPY ./annotation_api .

CMD ["gunicorn", "--forwarded-allow-ips=\"*\"", "-c", "gunicorn.py", "app:create_app()"]
