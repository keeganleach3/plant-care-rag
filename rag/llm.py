"""LLM call wrapper: `claude -p` (cc backend, Max plan) or the Anthropic SDK (api backend).

Copied with attribution from keeganleach3/job-pipeline `pipeline/llm.py` (MIT, 2026-09). The slim
`claude -p` flag set (no tools, no MCP, no settings) is what keeps a call at ~1.6K input tokens instead
of ~143K, and the system-prompt-file indirection works around cmd.exe's 8,191-char argument limit.
"""
import hashlib
import json
import random
import re
import shutil
import subprocess
import time
from dataclasses import dataclass

import anthropic

from rag.config import PRICES, ROOT, settings as _settings

_MAX_ATTEMPTS = 3
_RATE_LIMITED = re.compile(r"rate.?limit|overload", re.IGNORECASE)  # matched in error text only, never a success


@dataclass
class Result:
    parsed: dict
    usage: dict
    model: str
    cost_usd: float
    attempts: int


class LLMError(Exception):
    def __init__(self, kind: str, detail: str, attempts: int, usage: dict | None = None):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail
        self.attempts = attempts
        self.usage = usage

    def row(self) -> dict:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "attempts": self.attempts,
            "usage": self.usage,
        }


def validate(parsed, schema: dict) -> None:
    if not isinstance(parsed, dict):
        raise LLMError("schema_invalid", "structured output is not an object", 1)
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in parsed:
            raise LLMError("schema_invalid", f"missing required key: {key}", 1)
    _TYPE_MAP = {
        "string": str, "number": (int, float), "integer": int,
        "boolean": bool, "object": dict, "array": list,
    }
    for key, value in parsed.items():
        prop = properties.get(key)
        if prop is None:
            continue
        expected = _TYPE_MAP.get(prop.get("type"))
        if expected is not None and not isinstance(value, expected):
            raise LLMError("schema_invalid", f"{key} has wrong type", 1)
        if "enum" in prop and value not in prop["enum"]:
            raise LLMError("schema_invalid", f"{key} not in enum", 1)


def _backoff(n: int) -> float:
    return 2 ** n + random.random()


def _extract_trailing_json(stdout: str) -> dict:
    start = stdout.find("{")
    if start == -1:
        raise LLMError("schema_invalid", "no JSON object found in stdout", 1)
    try:
        obj, _ = json.JSONDecoder().raw_decode(stdout, start)
    except json.JSONDecodeError as exc:
        raise LLMError("schema_invalid", f"unparseable JSON in stdout: {exc}", 1) from exc
    return obj


def _cli_error_detail(payload: dict, returncode: int, stderr: str) -> str:
    """What the CLI said went wrong: subtype, result text, exit code, stderr tail. Never empty, at most 500 chars."""
    parts = (payload.get("subtype"), str(payload.get("result") or "")[:300], f"exit {returncode}", (stderr or "")[-300:])
    return ", ".join(str(p) for p in parts if p)[:500]


def _system_prompt_file(system: str):
    """`claude` is a .cmd launcher on Windows, so cmd.exe's 8,191-char command-line
    limit applies; a 20K-char system prompt as an argument fails with
    'The command line is too long'. Write it to a file keyed by its hash instead."""
    d = ROOT / ".rag-tmp"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"system-{hashlib.sha256(system.encode()).hexdigest()[:16]}.md"
    if not p.exists():
        p.write_text(system, encoding="utf-8")
    return str(p)


def _call_cc(system: str, user: str, schema: dict, model: str, effort: str, timeout_s: int) -> Result:
    claude = shutil.which("claude")
    if claude is None:
        raise LLMError("cli_error", "claude CLI not found on PATH", 0)
    try:
        system_prompt_file = _system_prompt_file(system)
    except OSError as exc:
        raise LLMError("cli_error", str(exc), 0) from exc
    cmd = [
        claude, "-p",
        "--model", model,
        "--effort", effort,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--no-session-persistence",
        "--tools", "",
        "--system-prompt-file", system_prompt_file,
        "--setting-sources", "",
        "--strict-mcp-config",
        "--mcp-config", '{"mcpServers":{}}',
    ]
    attempts = 0
    while True:
        attempts += 1
        try:
            proc = subprocess.run(
                cmd, input=user, capture_output=True,
                encoding="utf-8", errors="replace", timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMError("timeout", str(exc), attempts) from exc
        except OSError as exc:
            raise LLMError("cli_error", str(exc), attempts) from exc

        try:
            payload = _extract_trailing_json(proc.stdout)
        except LLMError as exc:
            if proc.returncode == 0:
                exc.attempts = attempts
                raise
            payload = {}  # a crashed CLI may print no JSON; its exit code and stderr still explain it

        if proc.returncode != 0 or payload.get("is_error"):
            detail = _cli_error_detail(payload, proc.returncode, proc.stderr)
            if _RATE_LIMITED.search(detail) and attempts < _MAX_ATTEMPTS:
                time.sleep(_backoff(attempts))
                continue
            raise LLMError("cli_error", detail, attempts, usage=payload.get("usage"))

        structured = payload.get("structured_output")
        if structured is None:
            raise LLMError("schema_invalid", "missing structured_output", attempts, usage=payload.get("usage"))

        model_usage = payload.get("modelUsage") or {}
        if model not in model_usage:
            raise LLMError("model_mismatch", f"requested {model}, modelUsage has {list(model_usage)}", attempts, usage=payload.get("usage"))

        try:
            validate(structured, schema)
        except LLMError as exc:
            exc.attempts = attempts
            exc.usage = payload.get("usage")
            raise

        return Result(
            parsed=structured,
            usage=payload.get("usage", {}),
            model=model,
            cost_usd=payload.get("total_cost_usd", 0.0),
            attempts=attempts,
        )


def _call_api(system: str, user: str, schema: dict, model: str, effort: str, timeout_s: int) -> Result:
    client = anthropic.Anthropic(
        api_key=_settings(required=("ANTHROPIC_API_KEY",))["ANTHROPIC_API_KEY"],
        timeout=timeout_s,
        max_retries=0,  # our loop retries, not the SDK's
    )
    # Haiku 4.5 predates adaptive thinking and `effort`; both are rejected there (claude-api skill table).
    extra = {} if model.startswith("claude-haiku") else {"thinking": {"type": "adaptive"}}
    output_config = {"format": {"type": "json_schema", "schema": schema}}
    if not model.startswith("claude-haiku"):
        output_config["effort"] = effort
    attempts = 0
    while True:
        attempts += 1
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config=output_config,
                **extra,
            )
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            is_5xx = isinstance(exc, anthropic.APIStatusError) and getattr(exc, "status_code", 0) >= 500
            retryable = isinstance(exc, (anthropic.RateLimitError, anthropic.APIConnectionError)) or is_5xx
            if retryable and attempts < _MAX_ATTEMPTS:
                time.sleep(_backoff(attempts))
                continue
            if isinstance(exc, anthropic.APITimeoutError):
                raise LLMError("timeout", str(exc), attempts) from exc
            raise LLMError("cli_error", str(exc), attempts) from exc

        if response.model != model:
            raise LLMError("model_mismatch", f"requested {model}, got {response.model}", attempts)
        if response.stop_reason == "refusal":
            raise LLMError("refusal", "model refused", attempts)

        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise LLMError("schema_invalid", "no text block in response", attempts)
        try:
            structured = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError("schema_invalid", f"non-JSON text block: {exc}", attempts) from exc

        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        try:
            validate(structured, schema)
        except LLMError as exc:
            exc.attempts = attempts
            exc.usage = usage
            raise

        in_price, out_price = PRICES.get(model, (0, 0))
        cost_usd = (usage["input_tokens"] * in_price + usage["output_tokens"] * out_price) / 1_000_000

        return Result(parsed=structured, usage=usage, model=response.model, cost_usd=cost_usd, attempts=attempts)


def call(system: str, user: str, schema: dict, *, model="claude-sonnet-5", effort="low", timeout_s=120) -> Result:
    backend = _settings(required=()).get("LLM_BACKEND", "cc")
    if backend == "api":
        return _call_api(system, user, schema, model, effort, timeout_s)
    return _call_cc(system, user, schema, model, effort, timeout_s)
