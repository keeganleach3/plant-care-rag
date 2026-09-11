"""API tests on the isolated test DB, a fake embedder, and a fake LLM."""
import pytest
from fastapi.testclient import TestClient

from rag import api, ingest
from rag.embed import Embedder
from rag.llm import Result
from tests.test_embed import FakeModel

HEAD = "---\ntitle: T\ngenus: alocasia\ntopic: pests\nverified: true\n---\n"


@pytest.fixture
def client(conn, tmp_path):
    (tmp_path / "t-a.md").write_text(HEAD + "\n## Mites\n\nAlocasia spider mites: wipe leaves, spray weekly.\n", encoding="utf-8")
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(tmp_path, conn, emb)

    def fake_call(system, user, schema, **kw):
        cited = [] if "pollinate" in user else ["t-a#mites"]
        return Result(parsed={"answer": "Wipe and spray weekly." if cited else "I don't have information on that in my notes.",
                              "citations": cited, "refused": not cited},
                      usage={"input_tokens": 10, "output_tokens": 5}, model="claude-sonnet-5", cost_usd=0.0, attempts=1)

    app = api.create_app(conn=conn, embedder=emb, call=fake_call)
    return TestClient(app)


def test_ask_returns_answer_citations_chunks_and_timings(client):
    r = client.post("/ask", json={"question": "alocasia spider mites"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Wipe and spray weekly." and body["refused"] is False
    assert body["citations"] == ["t-a#mites"]
    assert body["chunks"][0]["chunk_id"] == "t-a#mites" and "content" in body["chunks"][0]
    assert set(body["timings"]) == {"embed_ms", "retrieve_ms", "generate_ms", "total_ms"}
    assert body["params"] == {"k": 5, "mode": "vector", "genus": None}


def test_k_is_clamped_and_invalid_genus_dropped(client):
    r = client.post("/ask", json={"question": "mites", "k": 99, "genus": "hoya", "mode": "hybrid"})
    assert r.status_code == 200
    assert r.json()["params"] == {"k": 20, "mode": "hybrid", "genus": None}


def test_question_too_long_is_422(client):
    assert client.post("/ask", json={"question": "x" * 501}).status_code == 422


def test_bad_mode_is_422(client):
    assert client.post("/ask", json={"question": "mites", "mode": "magic"}).status_code == 422


def test_refusal_passes_through(client):
    body = client.post("/ask", json={"question": "how to pollinate"}).json()
    assert body["refused"] is True and body["citations"] == [] and body["chunks"]
