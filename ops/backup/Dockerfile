FROM ghcr.io/astral-sh/uv:0.11.2 AS uv
FROM postgres:17-bookworm
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends age python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
ENV UV_PYTHON_INSTALL_DIR=/opt/python
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY ops/backup/ /app/ops/backup/
ENTRYPOINT ["bash"]
