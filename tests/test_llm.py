"""Every backend failure path maps to an LLMError with the existing kinds only; no other
exception escapes `rag.llm`. Fakes `subprocess.run`, `shutil.which`, and `anthropic.Anthropic` —
no network, no DB (TEST_DB is set per the run rules but never touched here)."""
import json
import subprocess
import types

import anthropic
import httpx
import pytest

from rag import llm

SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _proc(stdout="", stderr="", returncode=0):
    return types.SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _response(model="claude-sonnet-5", stop_reason="end_turn", text='{"answer": "ok"}'):
    content = [types.SimpleNamespace(type="text", text=text)] if text is not None else []
    return types.SimpleNamespace(model=model, stop_reason=stop_reason, content=content,
                                  usage=types.SimpleNamespace(input_tokens=10, output_tokens=5))


def _fake_anthropic(create):
    """Returns a class standing in for anthropic.Anthropic; records constructor kwargs on .captured."""
    class Messages:
        def __init__(self):
            self.create = create

    class Anthropic:
        captured = {}

        def __init__(self, **kwargs):
            Anthropic.captured = kwargs
            self.messages = Messages()

    return Anthropic


@pytest.fixture
def cc(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "cc")
    monkeypatch.setattr(llm.shutil, "which", lambda name: "claude")
    monkeypatch.setattr(llm, "_system_prompt_file", lambda system: "sysfile.md")
    return monkeypatch


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm.time, "sleep", lambda *a, **kw: None)
    return monkeypatch


# --- cc backend (claude -p) ---

def test_cc_claude_not_on_path(cc):
    cc.setattr(llm.shutil, "which", lambda name: None)
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    err = exc_info.value
    assert err.kind == "cli_error"
    assert err.detail == "claude CLI not found on PATH"
    assert err.attempts == 0


def test_cc_stdout_without_json_object_is_schema_invalid(cc):
    cc.setattr(llm.subprocess, "run", lambda *a, **kw: _proc(stdout="not json at all", returncode=0))
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    assert exc_info.value.kind == "schema_invalid"


def test_cc_malformed_json_is_schema_invalid(cc):
    cc.setattr(llm.subprocess, "run", lambda *a, **kw: _proc(stdout='prefix {"is_error": tru', returncode=0))
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    assert exc_info.value.kind == "schema_invalid"


def test_cc_nonzero_exit_is_cli_error_even_when_stdout_has_no_json(cc):
    cc.setattr(llm.subprocess, "run", lambda *a, **kw: _proc(stdout="", stderr="fatal: segfault", returncode=2))
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    err = exc_info.value
    assert err.kind == "cli_error"
    assert "exit 2" in err.detail
    assert "segfault" in err.detail


def test_cc_is_error_with_empty_result_detail_never_empty(cc):
    payload = json.dumps({"is_error": True, "result": "", "subtype": None, "usage": {}})
    cc.setattr(llm.subprocess, "run", lambda *a, **kw: _proc(stdout=payload, stderr="", returncode=0))
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    err = exc_info.value
    assert err.kind == "cli_error"
    assert err.detail
    assert "exit 0" in err.detail


def test_cc_cli_error_detail_joins_subtype_exit_and_truncated_stderr_tail(cc):
    long_stderr = "HEAD_MARKER" + ("x" * 800) + "TAIL_MARKER"
    payload = json.dumps({"subtype": "error_during_execution"})
    cc.setattr(llm.subprocess, "run", lambda *a, **kw: _proc(stdout=payload, stderr=long_stderr, returncode=1))
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    err = exc_info.value
    assert err.kind == "cli_error"
    assert "error_during_execution" in err.detail
    assert "exit 1" in err.detail
    assert "TAIL_MARKER" in err.detail
    assert "HEAD_MARKER" not in err.detail
    assert len(long_stderr[-500:]) == 500  # sanity: fixture is actually long enough to truncate


def test_cc_timeout(cc):
    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    cc.setattr(llm.subprocess, "run", fake_run)
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    assert exc_info.value.kind == "timeout"


# --- api backend (Anthropic SDK) ---

def test_api_client_built_with_max_retries_zero(api):
    FakeAnthropic = _fake_anthropic(lambda **kw: _response())
    api.setattr(llm.anthropic, "Anthropic", FakeAnthropic)
    llm.call("sys", "user", SCHEMA)
    assert FakeAnthropic.captured.get("max_retries") == 0


def test_api_connection_error_exhausts_retries_then_cli_error(api):
    FakeAnthropic = _fake_anthropic(lambda **kw: (_ for _ in ()).throw(anthropic.APIConnectionError(request=REQUEST)))
    api.setattr(llm.anthropic, "Anthropic", FakeAnthropic)
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    err = exc_info.value
    assert err.kind == "cli_error"
    assert err.attempts == llm._MAX_ATTEMPTS


def test_api_timeout_error_exhausts_retries_then_timeout(api):
    FakeAnthropic = _fake_anthropic(lambda **kw: (_ for _ in ()).throw(anthropic.APITimeoutError(request=REQUEST)))
    api.setattr(llm.anthropic, "Anthropic", FakeAnthropic)
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    assert exc_info.value.kind == "timeout"


def test_api_connection_error_retried_then_succeeds(api):
    calls = {"n": 0}

    def create(**kw):
        calls["n"] += 1
        if calls["n"] < llm._MAX_ATTEMPTS:
            raise anthropic.APIConnectionError(request=REQUEST)
        return _response()

    FakeAnthropic = _fake_anthropic(create)
    api.setattr(llm.anthropic, "Anthropic", FakeAnthropic)
    result = llm.call("sys", "user", SCHEMA)
    assert result.attempts == llm._MAX_ATTEMPTS
    assert result.parsed == {"answer": "ok"}


def test_api_missing_text_block_is_schema_invalid(api):
    FakeAnthropic = _fake_anthropic(lambda **kw: _response(text=None))
    api.setattr(llm.anthropic, "Anthropic", FakeAnthropic)
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    assert exc_info.value.kind == "schema_invalid"


def test_api_non_json_text_is_schema_invalid(api):
    FakeAnthropic = _fake_anthropic(lambda **kw: _response(text="not json"))
    api.setattr(llm.anthropic, "Anthropic", FakeAnthropic)
    with pytest.raises(llm.LLMError) as exc_info:
        llm.call("sys", "user", SCHEMA)
    assert exc_info.value.kind == "schema_invalid"
