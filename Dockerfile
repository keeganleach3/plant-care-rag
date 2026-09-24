FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /usr/local/bin/

WORKDIR /app
ENV HF_HOME=/app/.cache/huggingface \
    UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH"

# Build entirely as root: code and venv stay root-owned so a compromised app process can't rewrite its own code.
# Layers from least to most often changed: dependencies, the embedding model, then the code.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Bake the embedding model into the image, pinned to the snapshot the stored vectors were embedded with
# (rag/config.py EMBED_MODELS["BAAI/bge-base-en-v1.5"]["revision"]), so a container never needs network at startup.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5', device='cpu', revision='a5beb1e3e68b9ab74eb54cfd186867f64f240e1a')"
ENV HF_HUB_OFFLINE=1

COPY . .

# appuser owns only its writable scratch dir; everything else above stays root-owned and read-only to it.
RUN useradd --create-home appuser && mkdir -p /app/.rag-tmp && chown appuser:appuser /app/.rag-tmp
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
