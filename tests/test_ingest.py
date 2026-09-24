"""Integration: real Docker Postgres. Skips if DATABASE_URL is unreachable."""
import pytest

from rag import db, ingest
from tests.test_embed import FakeModel
from rag.embed import Embedder

HEAD = "---\ntitle: T\ngenus: alocasia\ntopic: pests\nverified: true\n---\n"


@pytest.fixture
def corpus(tmp_path):
    (tmp_path / "t-a.md").write_text(HEAD + "\n## Mites\n\nSpray weekly.\n\n## Thrips\n\nBlue sticky cards.\n", encoding="utf-8")
    (tmp_path / "t-b.md").write_text(HEAD + "\n## Scale\n\nAlcohol swab.\n", encoding="utf-8")
    (tmp_path / "t-unverified.md").write_text(HEAD.replace("true", "false") + "\n## X\n\nY.\n", encoding="utf-8")
    return tmp_path


def _count(conn):
    return conn.execute("SELECT count(*) FROM chunks WHERE chunk_id LIKE 't-%'").fetchone()[0]


def _tables(conn):
    """Every column of every row, so 'exactly as before' includes ingested_at, embeddings and labels."""
    return (conn.execute("SELECT d::text FROM documents d ORDER BY id").fetchall(),
            conn.execute("SELECT c::text FROM chunks c ORDER BY id").fetchall())


class DiesOnSecondDoc(FakeModel):
    def encode(self, texts, **kw):
        if any("swab" in t for t in texts):  # t-b.md: the 2nd doc, after t-a.md's upserts have run
            raise RuntimeError("embedder died mid-ingest")
        return super().encode(texts, **kw)


def test_a_failure_on_the_second_doc_leaves_both_tables_exactly_as_before(conn, corpus):
    ingest.run(corpus, conn, Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()))
    before = _tables(conn)
    (corpus / "t-a.md").write_text(HEAD + "\n## Mites\n\nSpray twice weekly.\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="mid-ingest"):
        ingest.run(corpus, conn, Embedder("BAAI/bge-base-en-v1.5", model=DiesOnSecondDoc()), prune=True)
    assert _tables(conn) == before


def test_ingest_labels_every_chunk_with_its_embedder_and_a_reingest_relabels(conn, corpus):
    assert db.embed_models(conn) == set()
    ingest.run(corpus, conn, Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()))
    assert db.embed_models(conn) == {"BAAI/bge-base-en-v1.5"}
    ingest.run(corpus, conn, Embedder("nomic-ai/nomic-embed-text-v1.5", model=FakeModel()))
    assert db.embed_models(conn) == {"nomic-ai/nomic-embed-text-v1.5"}


def test_ingest_upserts_verified_docs_and_skips_unverified(conn, corpus):
    report = ingest.run(corpus, conn, Embedder("BAAI/bge-base-en-v1.5", model=FakeModel()))
    assert report.ingested == 2 and report.chunks == 3
    assert [r for r in report.skipped if "unverified" in r[0]] and "verified" in report.skipped[0][1]
    assert _count(conn) == 3
    row = conn.execute("SELECT genus, topic, heading, content, embedding IS NOT NULL FROM chunks WHERE chunk_id='t-a#mites'").fetchone()
    assert row == ("alocasia", "pests", "Mites", "Spray weekly.", True)


def test_reingest_is_idempotent_and_updates_in_place(conn, corpus):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(corpus, conn, emb)
    (corpus / "t-b.md").write_text(HEAD + "\n## Scale\n\nAlcohol swab, repeat in 7 days.\n", encoding="utf-8")
    report = ingest.run(corpus, conn, emb)
    assert report.chunks == 3 and _count(conn) == 3
    assert conn.execute("SELECT content FROM chunks WHERE chunk_id='t-b#scale'").fetchone()[0] == "Alcohol swab, repeat in 7 days."


def test_prune_refuses_when_nothing_was_ingested(conn, corpus, tmp_path):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(corpus, conn, emb)
    before = _tables(conn)
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="nothing was ingested"):
        ingest.run(empty_dir, conn, emb, prune=True)
    assert _tables(conn) == before


def test_prune_removes_chunks_no_longer_in_corpus(conn, corpus):
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(corpus, conn, emb)
    (corpus / "t-a.md").write_text(HEAD + "\n## Mites\n\nSpray weekly.\n", encoding="utf-8")
    ingest.run(corpus, conn, emb)
    assert _count(conn) == 3  # no prune → stale thrips chunk remains
    ingest.run(corpus, conn, emb, prune=True)
    assert _count(conn) == 2
    assert conn.execute("SELECT 1 FROM chunks WHERE chunk_id='t-a#thrips'").fetchone() is None
