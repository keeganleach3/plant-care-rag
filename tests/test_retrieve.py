"""Integration: real Docker Postgres with a fake (bag-of-chars) embedder."""
import psycopg
import pytest

from rag import db, ingest, retrieve
from rag.config import settings
from rag.embed import Embedder
from tests.test_embed import FakeModel


def head(genus, topic="pests"):
    return f"---\ntitle: T\ngenus: {genus}\ntopic: {topic}\nverified: true\n---\n"


@pytest.fixture
def conn():
    try:
        c = psycopg.connect(settings()["DATABASE_URL"], autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("database not reachable")
    db.register(c)
    yield c
    c.execute("DELETE FROM documents WHERE slug LIKE 'zz-test-%'")
    c.close()


@pytest.fixture
def seeded(conn, tmp_path):
    (tmp_path / "zz-test-alocasia.md").write_text(head("alocasia") + "\n## Spider mites on alocasia\n\nAlocasia spider mites: wipe leaves, spray weekly.\n", encoding="utf-8")
    (tmp_path / "zz-test-monstera.md").write_text(head("monstera") + "\n## Thrips on monstera\n\nMonstera thrips: blue sticky cards, systemic.\n", encoding="utf-8")
    (tmp_path / "zz-test-general.md").write_text(head("general") + "\n## Quarantine rule\n\nQuarantine every new plant fourteen days.\n", encoding="utf-8")
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(tmp_path, conn, emb)
    return conn, emb


def test_vector_mode_ranks_closest_chunk_first(seeded):
    conn, emb = seeded
    hits = retrieve.search(conn, emb, "alocasia spider mites spray", k=3)
    assert hits[0].chunk_id == "zz-test-alocasia#spider-mites-on-alocasia"
    assert len(hits) == 3 and hits[0].score >= hits[1].score >= hits[2].score
    assert hits[0].content.startswith("Alocasia spider mites") and hits[0].genus == "alocasia" and hits[0].heading


def test_genus_filter_excludes_other_genera_but_keeps_general(seeded):
    conn, emb = seeded
    ids = {h.chunk_id for h in retrieve.search(conn, emb, "pests", k=10, genus="monstera")}
    assert "zz-test-monstera#thrips-on-monstera" in ids
    assert "zz-test-general#quarantine-rule" in ids
    assert "zz-test-alocasia#spider-mites-on-alocasia" not in ids


def test_hybrid_mode_surfaces_keyword_match(seeded):
    conn, emb = seeded
    hits = retrieve.search(conn, emb, "quarantine", k=3, mode="hybrid")
    assert hits[0].chunk_id == "zz-test-general#quarantine-rule"
    assert all(h.content for h in hits)


def test_unknown_mode_rejected(seeded):
    conn, emb = seeded
    with pytest.raises(ValueError):
        retrieve.search(conn, emb, "x", mode="magic")
