"""Shared pipeline: a generation failure still returns what retrieval found (isolated test DB, fake embedder, fake LLM)."""
import pytest

from rag import ingest, pipeline
from rag.embed import Embedder
from rag.llm import LLMError, Result
from tests.test_embed import FakeModel

HEAD = "---\ntitle: T\ngenus: alocasia\ntopic: pests\nverified: true\n---\n"


def forged(*_args, **_kw):
    return Result(parsed={"answer": "Spray.", "citations": ["nope#x"], "refused": False},
                  usage={}, model="claude-sonnet-5", cost_usd=0.0, attempts=1)


@pytest.fixture
def emb(conn, tmp_path):
    (tmp_path / "t-a.md").write_text(HEAD + "\n## Mites\n\nAlocasia spider mites: wipe leaves, spray weekly.\n", encoding="utf-8")
    e = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(tmp_path, conn, e)
    return e


def test_generation_error_keeps_chunks_timings_and_the_requested_model(conn, emb):
    out = pipeline.ask(conn, emb, "alocasia spider mites", call=forged, model="claude-haiku-4-5")
    assert out["error"]["kind"] == "citation_invalid" and "answer" not in out and out["model"] == "claude-haiku-4-5"
    assert [c["chunk_id"] for c in out["chunks"]] == ["t-a#mites"]
    assert set(out["timings"]) == {"embed_ms", "retrieve_ms", "generate_ms", "total_ms"}


def test_decompose_searches_the_whole_question_and_each_clause(conn, emb):
    q = "how do i treat spider mites on alocasia and when should i quarantine new plants"
    out = pipeline.ask(conn, emb, q, call=forged, decompose=True)
    assert out["queries"] == [q, "how do i treat spider mites on alocasia", "when should i quarantine new plants"]
    assert out["params"]["decompose"] is True
    plain = pipeline.ask(conn, emb, q, call=forged)
    assert plain["queries"] == [q] and plain["params"]["decompose"] is False


def test_backend_error_records_its_attempts(conn, emb):
    def down(*_args, **_kw):
        raise LLMError("timeout", "no reply in 120 s", attempts=3)

    out = pipeline.ask(conn, emb, "alocasia spider mites", call=down)
    assert out["error"] == {"kind": "timeout", "detail": "no reply in 120 s", "attempts": 3, "usage": None}
