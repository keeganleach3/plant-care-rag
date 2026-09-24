FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /usr/local/bin/

# Own /app before anything lands in it: a later `chown -R` would copy every file into a new layer.
RUN useradd --create-home appuser && mkdir /app && chown appuser:appuser /app
USER appuser
WORKDIR /app
ENV HF_HOME=/app/.cache/huggingface \
    UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH"

# Layers from least to most often changed: dependencies, the embedding model, then the code.
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Bake the embedding model into the image so a container never needs network at startup.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5', device='cpu')"

COPY --chown=appuser:appuser . .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
