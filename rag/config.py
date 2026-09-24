import os
import re
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
# revision pins the exact snapshot behind the stored vectors, so a model's weights can't drift under a moving tag.
EMBED_MODELS = {
    "BAAI/bge-base-en-v1.5": {"dim": 768, "query_prefix": "Represent this sentence for searching relevant passages: ", "doc_prefix": "", "trust_remote_code": False, "revision": "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"},
    "nomic-ai/nomic-embed-text-v1.5": {"dim": 768, "query_prefix": "search_query: ", "doc_prefix": "search_document: ", "trust_remote_code": True, "revision": None},  # pin on first ingest with this model
}

_KEYS = ("DATABASE_URL", "LLM_BACKEND", "ANTHROPIC_API_KEY", "EMBED_MODEL", "API_KEY", "MAX_INFLIGHT")
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
        value = value.strip()
        end = value.find(value[:1], 1) if value[:1] in ("'", '"') else -1
        # quoted: taken whole, '#' included (an API key may hold one); unquoted: a comment starts at a '#' that opens the
        # value or follows whitespace, so `KEY=   # note` is empty, never the note
        value = value[1:end] if end > 0 else re.split(r"(?:^|\s)#", value, maxsplit=1)[0].strip()
        values[key.strip()] = value
    return values


def settings(required: tuple = _REQUIRED) -> dict:
    values = _parse_env(ROOT / ".env")
    for key in _KEYS:  # a real env var wins, so one run can switch backend: LLM_BACKEND=api uv run ...
        if os.environ.get(key):
            values[key] = os.environ[key]
    values.setdefault("LLM_BACKEND", "cc")
    values.setdefault("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
    values.setdefault("MAX_INFLIGHT", "4")
    for key in required:
        if not values.get(key):
            raise ConfigError(f"missing required config key: {key}")
    if values["LLM_BACKEND"] == "api" and not values.get("ANTHROPIC_API_KEY"):
        raise ConfigError("missing required config key: ANTHROPIC_API_KEY")
    if values["EMBED_MODEL"] not in EMBED_MODELS:
        raise ConfigError(f"unknown EMBED_MODEL: {values['EMBED_MODEL']}")
    if not values["MAX_INFLIGHT"].isdecimal() or int(values["MAX_INFLIGHT"]) < 1:
        raise ConfigError(f"MAX_INFLIGHT must be a positive integer: {values['MAX_INFLIGHT']!r}")
    return values
