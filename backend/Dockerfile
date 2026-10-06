FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app ./app
COPY knowledge ./knowledge
RUN uv sync --frozen --no-dev --extra semantic
ENV FASTEMBED_CACHE_PATH=/app/models
RUN uv run --no-sync python -c "from app.embeddings import SemanticEmbedder; from app.settings import Settings; s=Settings(); SemanticEmbedder(s.fastembed_model,s.fastembed_threads)"
RUN useradd --create-home --uid 10001 lumen && mkdir -p /data && chown lumen:lumen /data && chown -R lumen:lumen /app/models
USER lumen
ENV DATA_DIR=/data PYTHONUNBUFFERED=1 UV_NO_SYNC=1
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
