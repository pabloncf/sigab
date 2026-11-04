# Development image: code is bind-mounted by compose.yaml and runserver reloads on change.
FROM ghcr.io/astral-sh/uv:0.11.2 AS uv

FROM python:3.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
# The virtualenv lives outside /app so the bind mount does not hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --dev --no-install-project
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
