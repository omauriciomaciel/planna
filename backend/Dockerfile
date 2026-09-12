FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN useradd --create-home --uid 10001 planna
USER planna

EXPOSE 8010

CMD ["uv", "run", "--frozen", "--no-dev", "fastapi", "run", "--host", "0.0.0.0", "--port", "8010"]
