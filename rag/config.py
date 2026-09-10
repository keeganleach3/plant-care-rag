import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
PROMPTS = ROOT / "prompts"
RESULTS = ROOT / "eval" / "results"

GENERA = ("philodendron", "anthurium", "monstera", "alocasia", "general")
TOPICS = ("acclimation", "humidity", "light", "substrate-water", "pests", "quirks", "troubleshooting")

# USD per 1M tokens (input, output) — api backend cost accounting only.
PRICES = {
    "claude-sonnet-5": (2, 10),
    "claude-opus-5": (5, 25),
    "claude-haiku-4-5-20251001": (1, 5),
    "claude-haiku-4-5": (1, 5),
}

# Embedding models: dims must match chunks.embedding vector(768); prefixes are per-model and asymmetric.
EMBED_MODELS = {
    "BAAI/bge-base-en-v1.5": {"dim": 768, "query_prefix": "Represent this sentence for searching relevant passages: ", "doc_prefix": "", "trust_remote_code": False},
    "nomic-ai/nomic-embed-text-v1.5": {"dim": 768, "query_prefix": "search_query: ", "doc_prefix": "search_document: ", "trust_remote_code": True},
}

_KEYS = ("DATABASE_URL", "LLM_BACKEND", "ANTHROPIC_API_KEY", "EMBED_MODEL")
_REQUIRED = ("DATABASE_URL",)


class ConfigError(Exception):
    pass


def _parse_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split("#", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key.strip()] = value
    return values


def settings(required: tuple = _REQUIRED) -> dict:
    values = _parse_env(ROOT / ".env")
    for key in _KEYS:  # a real env var wins, so one run can switch backend: LLM_BACKEND=api uv run ...
        if os.environ.get(key):
            values[key] = os.environ[key]
    values.setdefault("LLM_BACKEND", "cc")
    values.setdefault("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
    for key in required:
        if not values.get(key):
            raise ConfigError(f"missing required config key: {key}")
    if values["LLM_BACKEND"] == "api" and not values.get("ANTHROPIC_API_KEY"):
        raise ConfigError("missing required config key: ANTHROPIC_API_KEY")
    if values["EMBED_MODEL"] not in EMBED_MODELS:
        raise ConfigError(f"unknown EMBED_MODEL: {values['EMBED_MODEL']}")
    return values
