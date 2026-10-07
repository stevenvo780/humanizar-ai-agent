FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app ./app
COPY knowledge ./knowledge
RUN uv sync --frozen --no-dev --extra semantic
ENV FASTEMBED_CACHE_PATH=/app/models
RUN uv run --no-sync python -c "from app.knowledge.embeddings import SemanticEmbedder; from app.core.settings import Settings; s=Settings(); SemanticEmbedder(s.fastembed_model,s.fastembed_threads)"
RUN useradd --create-home --uid 10001 lumen && mkdir -p /data && chown lumen:lumen /data && chown -R lumen:lumen /app/models
USER lumen
# libpq bundled with psycopg uses OpenSSL's default paths, which may differ from
# Debian's CA store. Keep verify-full/system trust pointed at the installed CAs.
ENV DATA_DIR=/data PYTHONUNBUFFERED=1 UV_NO_SYNC=1 SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt SSL_CERT_DIR=/etc/ssl/certs
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
