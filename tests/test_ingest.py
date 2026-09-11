"""Integration: real Docker Postgres. Skips if DATABASE_URL is unreachable."""
import psycopg
import pytest

from rag import db, ingest
from rag.config import settings
from tests.test_embed import FakeModel
from rag.embed import Embedder

HEAD = "---\ntitle: T\ngenus: alocasia\ntopic: pests\nverified: true\n---\n"


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
def corpus(tmp_path):
    (tmp_path / "zz-test-a.md").write_text(HEAD + "\n## Mites\n\nSpray weekly.\n\n## Thrips\n\nBlue sticky cards.\n", encoding="utf-8")
    (tmp_path / "zz-test-b.md").write_text(HEAD + "\n## Scale\n\nAlcohol swab.\n", encoding="utf-8")
    (tmp_path / "zz-test-unverified.md").write_text(HEAD.replace("true", "false") + "\n## X\n\nY.\n", encoding="utf-8")
    return tmp_path


def _count(conn):
    return conn.execute("SELECT count(*) FROM chunks WHERE chunk_id LIKE 'zz-test-%'").fetchone()[0]


def test_ingest_upserts_verified_docs_and_skips_unverified(conn, corpus):
    report = ingest.run(corpus, conn, Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()))
    assert report.ingested == 2 and report.chunks == 3
    assert [r for r in report.skipped if "unverified" in r[0]] and "verified" in report.skipped[0][1]
    assert _count(conn) == 3
    row = conn.execute("SELECT genus, topic, heading, content, embedding IS NOT NULL FROM chunks WHERE chunk_id='zz-test-a#mites'").fetchone()
    assert row == ("alocasia", "pests", "Mites", "Spray weekly.", True)


def test_reingest_is_idempotent_and_updates_in_place(conn, corpus):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(corpus, conn, emb)
    (corpus / "zz-test-b.md").write_text(HEAD + "\n## Scale\n\nAlcohol swab, repeat in 7 days.\n", encoding="utf-8")
    report = ingest.run(corpus, conn, emb)
    assert report.chunks == 3 and _count(conn) == 3
    assert conn.execute("SELECT content FROM chunks WHERE chunk_id='zz-test-b#scale'").fetchone()[0] == "Alcohol swab, repeat in 7 days."


def test_prune_removes_chunks_no_longer_in_corpus(conn, corpus):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(corpus, conn, emb)
    (corpus / "zz-test-a.md").write_text(HEAD + "\n## Mites\n\nSpray weekly.\n", encoding="utf-8")
    ingest.run(corpus, conn, emb)
    assert _count(conn) == 3  # no prune → stale thrips chunk remains
    ingest.run(corpus, conn, emb, prune=True)
    assert _count(conn) == 2
    assert conn.execute("SELECT 1 FROM chunks WHERE chunk_id='zz-test-a#thrips'").fetchone() is None
