FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY ./airial_api/pyproject.toml ./airial_api/uv.lock ./
RUN uv sync --locked

COPY ./airial_api .

CMD ["uv", "run", "python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8000", "--debug"]
