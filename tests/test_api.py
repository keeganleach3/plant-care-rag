"""API tests on the isolated test DB, a fake embedder, and a fake LLM."""
import hashlib
import json
import logging
import re
import secrets
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from rag import api, config, ingest
from rag.embed import Embedder
from rag.llm import LLMError, Result
from tests.test_embed import FakeModel
from tests.test_pipeline import forged

HEAD = "---\ntitle: T\ngenus: alocasia\ntopic: pests\nverified: true\n---\n"
Q = {"question": "alocasia spider mites"}
LOG_KEYS = ["request_id", "status", "total_ms", "k", "mode", "decompose", "n_queries", "chunk_ids", "citations", "refused",
            "error_kind", "error_detail", "model", "usage", "question_chars", "question_sha"]
DOCS = ("/docs", "/redoc", "/openapi.json")
SERVED_KEYS = ("API_KEY", "MAX_INFLIGHT", "LLM_BACKEND")


@pytest.fixture(autouse=True)
def served_env(monkeypatch):
    """API_KEY, MAX_INFLIGHT and LLM_BACKEND come from each test's own env, never the developer's .env or shell; the claude
    CLI counts as installed (CI has none) unless a test says otherwise."""
    parse = config._parse_env
    monkeypatch.setattr(config, "_parse_env", lambda path: {k: v for k, v in parse(path).items() if k not in SERVED_KEYS})
    for key in SERVED_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")


def fake_call(system, user, schema, **kw):
    cited = [] if "pollinate" in user else ["t-a#mites"]
    return Result(parsed={"answer": "Wipe and spray weekly." if cited else "I don't have information on that in my notes.",
                          "citations": cited, "refused": not cited},
                  usage={"input_tokens": 10, "output_tokens": 5}, model="claude-sonnet-5", cost_usd=0.0, attempts=1)


def _seed(conn, tmp_path) -> Embedder:
    (tmp_path / "t-a.md").write_text(HEAD + "\n## Mites\n\nAlocasia spider mites: wipe leaves, spray weekly.\n", encoding="utf-8")
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(tmp_path, conn, emb)
    return emb


def _client(conn, tmp_path, call):
    return TestClient(api.create_app(conn=conn, embedder=_seed(conn, tmp_path), call=call))


def _lines(caplog) -> list[dict]:
    return [json.loads(r.getMessage()) for r in caplog.records if r.name == "rag.api" and r.levelno == logging.INFO]


def _dead(url):
    c = psycopg.connect(url)
    c.close()
    return c


@pytest.fixture
def client(conn, tmp_path):
    return _client(conn, tmp_path, fake_call)


def test_ask_needs_the_bearer_key_when_api_key_is_set(conn, tmp_path, monkeypatch, caplog):
    key = secrets.token_urlsafe(32)
    monkeypatch.setenv("API_KEY", key)
    client = _client(conn, tmp_path, fake_call)
    bad = [None, "", "Bearer", "Bearer wrong", f"Bearer {key}x", f"Bearer {key[:-1]}", key, f"Basic {key}",
           f"Bearer  {key}", b"Bearer \xe9" + key.encode()]
    for auth in bad:
        r = client.post("/ask", json=Q, headers={} if auth is None else {"Authorization": auth})
        assert r.status_code == 401 and r.headers["WWW-Authenticate"] == "Bearer", auth
        assert key not in r.text
    assert client.post("/ask", json=Q, headers={"Authorization": f"Bearer {key}"}).status_code == 200
    assert client.get("/healthz").status_code == 200 and client.get("/readyz").status_code == 200
    assert [line["status"] for line in _lines(caplog)] == [401] * len(bad) + [200]
    assert key not in caplog.text


def test_sources_needs_the_bearer_key_when_api_key_is_set(conn, tmp_path, monkeypatch):
    key = secrets.token_urlsafe(32)
    monkeypatch.setenv("API_KEY", key)
    client = _client(conn, tmp_path, fake_call)
    for auth in (None, f"Bearer {key}x"):
        r = client.get("/sources", headers={} if auth is None else {"Authorization": auth})
        assert r.status_code == 401 and r.headers["WWW-Authenticate"] == "Bearer" and key not in r.text, auth
    assert client.get("/sources", headers={"Authorization": f"Bearer {key}"}).status_code == 200


def test_open_ask_is_warned_once_at_startup(conn, monkeypatch, caplog):
    def warnings():
        return [r.getMessage() for r in caplog.records if r.name == "rag.api" and r.levelno >= logging.WARNING]

    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    with TestClient(api.create_app(conn=conn, embedder=emb)):
        pass
    assert len(warnings()) == 1 and "/ask" in warnings()[0] and "/sources" in warnings()[0]
    caplog.clear()
    monkeypatch.setenv("API_KEY", secrets.token_urlsafe(32))
    with TestClient(api.create_app(conn=conn, embedder=emb)):
        pass
    assert warnings() == []


def test_request_id_is_echoed_only_when_well_formed(client):
    for good in ("req-1.a_B", "x" * 64):
        assert client.get("/healthz", headers={"X-Request-ID": good}).headers["X-Request-ID"] == good
    fresh = [client.get("/healthz", headers={"X-Request-ID": bad}).headers["X-Request-ID"]
             for bad in ("x" * 65, "", "has space", "semi;colon", "ok\n", b"caf\xc3\xa9")]
    fresh.append(client.get("/healthz").headers["X-Request-ID"])
    assert all(re.fullmatch(r"[0-9a-f]{32}", rid) for rid in fresh) and len(set(fresh)) == len(fresh)
    assert client.post("/ask", json={"question": ""}, headers={"X-Request-ID": "r-422"}).headers["X-Request-ID"] == "r-422"


def test_one_request_over_max_inflight_is_shed_with_503(conn, tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_INFLIGHT", "2")
    gate, entered = threading.Event(), threading.Semaphore(0)

    def held_call(*args, **kw):
        entered.release()
        gate.wait(10)
        return fake_call(*args, **kw)

    client = _client(conn, tmp_path, held_call)
    with ThreadPoolExecutor(3) as pool:
        try:
            futures = [pool.submit(client.post, "/ask", json=Q) for _ in range(3)]
            shed = next(as_completed(futures, timeout=10)).result()
            held = [entered.acquire(timeout=10) for _ in range(2)]
        finally:
            gate.set()
        codes = sorted(f.result().status_code for f in futures)
    assert held == [True, True] and codes == [200, 200, 503]
    assert shed.status_code == 503 and shed.headers["Retry-After"] == "5" and shed.json() == {"detail": "busy"}
    assert client.post("/ask", json=Q).status_code == 200


def test_a_crashed_generation_gives_its_slot_back(conn, tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("MAX_INFLIGHT", "1")
    calls = []

    def crash_first(*args, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return fake_call(*args, **kw)

    client = _client(conn, tmp_path, crash_first)
    r = client.post("/ask", json=Q, headers={"X-Request-ID": "crash-1"})
    assert r.status_code == 500 and r.headers["X-Request-ID"] == "crash-1" and "boom" not in r.text
    assert client.post("/ask", json=Q).status_code == 200
    assert [line["status"] for line in _lines(caplog)] == [500, 200]


@pytest.mark.parametrize("value", ["0", "-1", "four", "2.5"])
def test_max_inflight_must_be_a_positive_integer(monkeypatch, value):
    monkeypatch.setenv("MAX_INFLIGHT", value)
    with pytest.raises(config.ConfigError, match="MAX_INFLIGHT"):
        api.create_app()


def test_pool_replaces_connections_killed_under_it(conn, test_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    emb = _seed(conn, tmp_path)
    with TestClient(api.create_app(embedder=emb, call=fake_call)) as client:
        assert client.post("/ask", json=Q).status_code == 200
        killed = conn.execute("SELECT pg_terminate_backend(pid, 5000) FROM pg_stat_activity WHERE datname = current_database() "
                              "AND backend_type = 'client backend' AND pid <> pg_backend_pid()").fetchall()
        assert killed and all(ok for (ok,) in killed)
        assert client.post("/ask", json=Q).status_code == 200
        assert client.get("/readyz").json() == {"status": "ready", "chunks": 1}


def test_readyz_names_each_failed_check(conn, test_db_url, tmp_path):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    r = TestClient(api.create_app(conn=conn, embedder=emb)).get("/readyz")
    assert r.status_code == 503 and r.json() == {"status": "not ready", "failed": ["chunks"]}
    assert TestClient(api.create_app(conn=conn)).get("/readyz").json()["failed"] == ["chunks", "embedder"]
    assert TestClient(api.create_app(conn=_dead(test_db_url), embedder=emb)).get("/readyz").json()["failed"] == ["db"]
    _seed(conn, tmp_path)
    r = TestClient(api.create_app(conn=conn, embedder=emb)).get("/readyz")
    assert r.status_code == 200 and r.json() == {"status": "ready", "chunks": 1}


def test_healthz_touches_nothing(test_db_url):
    r = TestClient(api.create_app(conn=_dead(test_db_url))).get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_one_json_log_line_per_ask_with_the_request_id_never_the_question(client, caplog):
    q = "alocasia spider mites, asks Zelda"
    assert client.post("/ask", json={"question": q}, headers={"X-Request-ID": "trace-42"}).status_code == 200
    client.get("/healthz")
    [line] = _lines(caplog)
    assert list(line) == LOG_KEYS and line["total_ms"] > 0
    assert line | {"total_ms": None} == {
        "request_id": "trace-42", "status": 200, "total_ms": None, "k": 5, "mode": "vector", "decompose": True,
        "n_queries": 1, "chunk_ids": ["t-a#mites"], "citations": ["t-a#mites"], "refused": False, "error_kind": None,
        "error_detail": None, "model": "claude-sonnet-5", "usage": {"input_tokens": 10, "output_tokens": 5}, "question_chars": len(q),
        "question_sha": hashlib.sha256(q.encode()).hexdigest()[:12]}
    assert "Zelda" not in caplog.text


def test_ask_returns_answer_citations_chunks_and_timings(client):
    r = client.post("/ask", json={"question": "alocasia spider mites"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "citations", "refused", "chunks", "params", "queries", "model", "usage", "timings"}
    assert body["answer"] == "Wipe and spray weekly." and body["refused"] is False
    assert body["citations"] == ["t-a#mites"]
    assert body["chunks"][0]["chunk_id"] == "t-a#mites" and "content" in body["chunks"][0]
    assert set(body["timings"]) == {"embed_ms", "retrieve_ms", "generate_ms", "total_ms"}
    assert body["params"] == {"k": 5, "mode": "vector", "genus": None, "decompose": True}
    assert body["queries"] == ["alocasia spider mites"]


def test_k_is_clamped_and_invalid_genus_dropped(client):
    r = client.post("/ask", json={"question": "mites", "k": 99, "genus": "hoya", "mode": "hybrid"})
    assert r.status_code == 200
    assert r.json()["params"] == {"k": 20, "mode": "hybrid", "genus": None, "decompose": True}


def test_decompose_is_served_by_default_and_can_be_turned_off(client):
    q = "how do i treat spider mites on alocasia and when should i quarantine new plants"
    assert len(client.post("/ask", json={"question": q}).json()["queries"]) == 3
    body = client.post("/ask", json={"question": q, "decompose": False}).json()
    assert body["params"]["decompose"] is False and body["queries"] == [q]


def test_question_too_long_is_422(client):
    assert client.post("/ask", json={"question": "x" * 501}).status_code == 422


def test_bad_mode_is_422(client):
    assert client.post("/ask", json={"question": "mites", "mode": "magic"}).status_code == 422


def test_refusal_passes_through(client):
    body = client.post("/ask", json={"question": "how to pollinate"}).json()
    assert body["refused"] is True and body["citations"] == [] and body["chunks"]


def test_generation_error_is_502_with_its_kind(conn, tmp_path, caplog):
    r = _client(conn, tmp_path, forged).post("/ask", json=Q)
    assert r.status_code == 502 and r.json() == {"detail": "citation_invalid"}  # the kind only; internals stay in the log
    [line] = _lines(caplog)
    assert line["status"] == 502 and line["error_kind"] == "citation_invalid" and line["citations"] is None
    assert "not in retrieved set" in line["error_detail"]


def test_readyz_and_startup_refuse_vectors_from_another_embedding_model(conn, tmp_path):
    (tmp_path / "t-a.md").write_text(HEAD + "\n## Mites\n\nAlocasia spider mites: wipe leaves, spray weekly.\n", encoding="utf-8")
    ingest.run(tmp_path, conn, Embedder("nomic-ai/nomic-embed-text-v1.5", model=FakeModel()))
    app = api.create_app(conn=conn, embedder=Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()), call=fake_call)
    r = TestClient(app).get("/readyz")
    assert r.status_code == 503 and r.json() == {"status": "not ready", "failed": ["embed_model"]}
    with pytest.raises(RuntimeError, match="nomic-ai/nomic-embed-text-v1.5"):
        with TestClient(app):
            pass


def test_an_unreachable_database_fails_ask_readyz_and_sources_within_seconds(monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", "postgresql://plant:plant@127.0.0.1:1/plantcare")
    monkeypatch.setenv("MAX_INFLIGHT", "1")
    with TestClient(api.create_app(embedder=Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()), call=fake_call)) as client:
        for _ in range(2):  # the second is not shed as busy: the first gave its slot back
            t = time.perf_counter()
            r = client.post("/ask", json=Q)
            assert r.status_code == 503 and r.json() == {"detail": "db"} and r.headers["Retry-After"] == "5"
            assert time.perf_counter() - t < 10
        t = time.perf_counter()
        r = client.get("/readyz")
        assert r.status_code == 503 and r.json()["failed"] == ["db"] and time.perf_counter() - t < 10
        t = time.perf_counter()
        r = client.get("/sources")
        assert r.status_code == 503 and r.json() == {"detail": "db"} and r.headers["Retry-After"] == "5"
        assert time.perf_counter() - t < 10
    warned = [rec.getMessage() for rec in caplog.records if rec.name == "rag.api" and rec.levelno == logging.WARNING]
    assert any("first /ask" in w for w in warned)  # the embed_model check waits for the database


def test_the_paid_backend_refuses_to_start_without_an_api_key(conn, monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unused")
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    with pytest.raises(config.ConfigError, match="API_KEY"), TestClient(api.create_app(conn=conn, embedder=emb)):
        pass
    monkeypatch.setenv("API_KEY", secrets.token_urlsafe(32))
    with TestClient(api.create_app(conn=conn, embedder=emb)) as client:
        assert client.get("/healthz").status_code == 200


def test_a_short_api_key_refuses_to_start_without_echoing_it(conn, monkeypatch, caplog):
    key = secrets.token_urlsafe(32)
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    monkeypatch.setenv("API_KEY", key[:31])
    with pytest.raises(config.ConfigError, match="32") as exc, TestClient(api.create_app(conn=conn, embedder=emb)):
        pass
    assert key[:31] not in str(exc.value) + caplog.text
    monkeypatch.setenv("API_KEY", key[:32])
    with TestClient(api.create_app(conn=conn, embedder=emb)):
        pass


def test_docs_and_schema_are_hidden_when_api_key_is_set(conn, monkeypatch):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    monkeypatch.setenv("API_KEY", secrets.token_urlsafe(32))
    keyed = TestClient(api.create_app(conn=conn, embedder=emb))
    assert [keyed.get(p).status_code for p in DOCS] == [404, 404, 404]
    monkeypatch.delenv("API_KEY")
    local = TestClient(api.create_app(conn=conn, embedder=emb))
    assert [local.get(p).status_code for p in DOCS] == [200, 200, 200]


def test_pooled_connections_carry_the_db_timeouts(conn, test_db_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    pools = []

    class Recorded(ConnectionPool):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            pools.append(self)

    monkeypatch.setattr(api, "ConnectionPool", Recorded)
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    with TestClient(api.create_app(embedder=emb, call=fake_call)), pools[0].connection() as c:
        assert c.execute("SHOW statement_timeout").fetchone()[0] == "10s"
        assert c.info.get_parameters()["connect_timeout"] == "5" and c.autocommit


def test_a_schema_error_is_not_taken_for_an_unreachable_database(test_db_url):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    with psycopg.connect(test_db_url, autocommit=True) as old:
        old.execute("CREATE TEMP TABLE chunks (chunk_id text)")  # shadows the real table: a schema with no embed_model
        app = api.create_app(conn=old, embedder=emb)
        r = TestClient(app).get("/readyz")
        assert r.status_code == 503 and r.json() == {"status": "not ready", "failed": ["schema"]}
        with pytest.raises(psycopg.errors.UndefinedColumn), TestClient(app):
            pass


def test_the_embed_model_check_deferred_at_startup_runs_on_the_first_ask(conn, tmp_path, monkeypatch):
    (tmp_path / "t-a.md").write_text(HEAD + "\n## Mites\n\nAlocasia spider mites: wipe leaves, spray weekly.\n", encoding="utf-8")
    ingest.run(tmp_path, conn, Embedder("nomic-ai/nomic-embed-text-v1.5", model=FakeModel()))
    real, calls = api.db.embed_models, []

    def down_at_startup(c):
        calls.append(1)
        if len(calls) == 1:
            raise psycopg.OperationalError("connection refused")
        return real(c)

    monkeypatch.setattr(api.db, "embed_models", down_at_startup)
    app = api.create_app(conn=conn, embedder=Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()), call=fake_call)
    with TestClient(app) as client:
        r = client.post("/ask", json=Q)
        assert r.status_code == 503 and r.json() == {"detail": "embed_model"}
        conn.execute("UPDATE chunks SET embed_model = 'BAAI/bge-base-en-v1.5'")  # re-ingested with the served model
        assert [client.post("/ask", json=Q).status_code for _ in range(2)] == [200, 200]
    assert len(calls) == 3  # checked until it passed, then never again


def _body(size: int) -> bytes:
    """Q as JSON, padded with insignificant whitespace to exactly `size` bytes."""
    head = json.dumps(Q).encode()[:-1]
    return head + b" " * (size - len(head) - 1) + b"}"


def test_ask_needs_a_content_length_of_at_most_4096_bytes(client, caplog):
    ctype = {"Content-Type": "application/json"}
    assert client.post("/ask", content=_body(4097), headers=ctype).status_code == 413
    assert client.post("/ask", content=iter([_body(100)]), headers=ctype).status_code == 411  # chunked, no Content-Length
    # h11 frames the body by Transfer-Encoding when both are sent, so a small Content-Length beside it bounds nothing
    assert client.post("/ask", content=_body(100), headers=ctype | {"Transfer-Encoding": "chunked"}).status_code == 411
    assert client.post("/ask", content=_body(4096), headers=ctype).status_code == 200
    assert [line["status"] for line in _lines(caplog)] == [413, 411, 411, 200]


def test_the_question_is_masked_in_the_logged_error_detail(conn, tmp_path, caplog):
    q = "alocasia spider mites, asks Zelda"

    def echoing(system, user, schema, **kw):
        raise LLMError("cli_error", f"exit 1: {q} | stderr: {q}", 1)

    r = _client(conn, tmp_path, echoing).post("/ask", json={"question": q})
    assert r.status_code == 502 and r.json() == {"detail": "cli_error"}
    [line] = _lines(caplog)
    assert line["error_detail"] == "exit 1: [question] | stderr: [question]" and "Zelda" not in caplog.text


def test_readyz_fails_llm_when_the_cc_backend_has_no_claude_cli(conn, tmp_path, monkeypatch):
    emb = _seed(conn, tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "claude" else f"/usr/bin/{name}")
    r = TestClient(api.create_app(conn=conn, embedder=emb)).get("/readyz")
    assert r.status_code == 503 and r.json() == {"status": "not ready", "failed": ["llm"]}
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unused")
    assert TestClient(api.create_app(conn=conn, embedder=emb)).get("/readyz").status_code == 200  # no CLI on that path


def test_sources_lists_every_indexed_section_by_note_genus_then_title_in_ingest_order(conn, tmp_path):
    # file (ingest) order runs opposite to genus-then-title, and headings run opposite to ingest order
    for stem, genus, topic, title, body in [
            ("a-mon", "monstera", "light", "Light", "## Window\n\nEast window.\n\n## Grow lights\n\nTwelve hours.\n"),
            ("b-alo", "alocasia", "pests", "Pests", "## Thrips\n\nBlue sticky cards.\n\n## Mites\n\nSpray weekly.\n"),
            ("c-alo", "alocasia", "humidity", "Humidity", "## Tent\n\nTent it.\n")]:
        (tmp_path / f"{stem}.md").write_text(f"---\ntitle: {title}\ngenus: {genus}\ntopic: {topic}\nverified: true\n---\n\n{body}",
                                             encoding="utf-8")
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(tmp_path, conn, emb)
    r = TestClient(api.create_app(conn=conn, embedder=emb)).get("/sources")
    assert r.status_code == 200 and r.json() == {"embed_model": "BAAI/bge-base-en-v1.5", "notes": [
        {"slug": "c-alo", "title": "Humidity", "genus": "alocasia", "topic": "humidity",
         "sections": [{"chunk_id": "c-alo#tent", "heading": "Tent", "content": "Tent it."}]},
        {"slug": "b-alo", "title": "Pests", "genus": "alocasia", "topic": "pests",
         "sections": [{"chunk_id": "b-alo#thrips", "heading": "Thrips", "content": "Blue sticky cards."},
                      {"chunk_id": "b-alo#mites", "heading": "Mites", "content": "Spray weekly."}]},
        {"slug": "a-mon", "title": "Light", "genus": "monstera", "topic": "light",
         "sections": [{"chunk_id": "a-mon#window", "heading": "Window", "content": "East window."},
                      {"chunk_id": "a-mon#grow-lights", "heading": "Grow lights", "content": "Twelve hours."}]}]}
    assert sum(len(n["sections"]) for n in r.json()["notes"]) == conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
