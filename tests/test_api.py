"""API tests on the isolated test DB, a fake embedder, and a fake LLM."""
import hashlib
import json
import logging
import re
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg
import pytest
from fastapi.testclient import TestClient

from rag import api, config, ingest
from rag.embed import Embedder
from rag.llm import Result
from tests.test_embed import FakeModel
from tests.test_pipeline import forged

HEAD = "---\ntitle: T\ngenus: alocasia\ntopic: pests\nverified: true\n---\n"
Q = {"question": "alocasia spider mites"}
LOG_KEYS = ["request_id", "status", "total_ms", "k", "mode", "decompose", "n_queries", "chunk_ids", "citations", "refused",
            "error_kind", "error_detail", "model", "usage", "question_chars", "question_sha"]


@pytest.fixture(autouse=True)
def served_env(monkeypatch):
    """API_KEY and MAX_INFLIGHT come from each test's own env, never the developer's .env or shell."""
    parse = config._parse_env
    monkeypatch.setattr(config, "_parse_env",
                        lambda path: {k: v for k, v in parse(path).items() if k not in ("API_KEY", "MAX_INFLIGHT")})
    for key in ("API_KEY", "MAX_INFLIGHT"):
        monkeypatch.delenv(key, raising=False)


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
    key = secrets.token_urlsafe(16)
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


def test_open_ask_is_warned_once_at_startup(conn, monkeypatch, caplog):
    def warnings():
        return [r.getMessage() for r in caplog.records if r.name == "rag.api" and r.levelno >= logging.WARNING]

    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    with TestClient(api.create_app(conn=conn, embedder=emb)):
        pass
    assert len(warnings()) == 1 and "/ask" in warnings()[0]
    caplog.clear()
    monkeypatch.setenv("API_KEY", secrets.token_urlsafe(16))
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


def test_readyz_gives_up_on_an_unreachable_database_within_seconds(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://plant:plant@127.0.0.1:1/plantcare")
    with TestClient(api.create_app(embedder=Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()), call=fake_call)) as client:
        t = time.perf_counter()
        r = client.get("/readyz")
        assert r.status_code == 503 and r.json()["failed"] == ["db"] and time.perf_counter() - t < 10
