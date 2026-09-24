"""Integration: real Docker Postgres with a fake (bag-of-chars) embedder."""
import pytest

from rag import db, ingest, retrieve
from rag.embed import Embedder
from tests.test_embed import FakeModel


def head(genus, topic="pests"):
    return f"---\ntitle: T\ngenus: {genus}\ntopic: {topic}\nverified: true\n---\n"


@pytest.fixture
def seeded(conn, tmp_path):
    (tmp_path / "t-alocasia.md").write_text(head("alocasia") + "\n## Spider mites on alocasia\n\nAlocasia spider mites: wipe leaves, spray weekly.\n", encoding="utf-8")
    (tmp_path / "t-monstera.md").write_text(head("monstera") + "\n## Thrips on monstera\n\nMonstera thrips: blue sticky cards, systemic.\n", encoding="utf-8")
    (tmp_path / "t-general.md").write_text(head("general") + "\n## Quarantine rule\n\nQuarantine every new plant fourteen days.\n", encoding="utf-8")
    emb = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    ingest.run(tmp_path, conn, emb)
    return conn, emb


def test_vector_mode_ranks_closest_chunk_first(seeded):
    conn, emb = seeded
    hits = retrieve.search(conn, emb, "alocasia spider mites spray", k=3)
    assert hits[0].chunk_id == "t-alocasia#spider-mites-on-alocasia"
    assert len(hits) == 3 and hits[0].score >= hits[1].score >= hits[2].score
    assert hits[0].content.startswith("Alocasia spider mites") and hits[0].genus == "alocasia" and hits[0].heading


def test_genus_filter_excludes_other_genera_but_keeps_general(seeded):
    conn, emb = seeded
    ids = {h.chunk_id for h in retrieve.search(conn, emb, "pests", k=10, genus="monstera")}
    assert "t-monstera#thrips-on-monstera" in ids
    assert "t-general#quarantine-rule" in ids
    assert "t-alocasia#spider-mites-on-alocasia" not in ids


def test_hybrid_mode_surfaces_keyword_match(seeded):
    conn, emb = seeded
    hits = retrieve.search(conn, emb, "quarantine", k=3, mode="hybrid")
    assert hits[0].chunk_id == "t-general#quarantine-rule"
    assert all(h.content for h in hits)


def test_unknown_mode_rejected(seeded):
    conn, emb = seeded
    with pytest.raises(ValueError):
        retrieve.search(conn, emb, "x", mode="magic")


def test_clauses_split_where_and_opens_a_new_question():
    q = "just potted my plantlets, how wet should the mix stay and when do i start feeding them"
    assert retrieve.clauses(q) == ["just potted my plantlets, how wet should the mix stay", "when do i start feeding them"]


def test_clauses_split_at_question_marks():
    assert retrieve.clauses("How humid should the dome be? When can I start feeding them?") == [
        "How humid should the dome be", "When can I start feeding them"]


@pytest.mark.parametrize("q", [
    "do monstera and anthurium need the same soil mix",                     # "and" joins nouns, not questions
    "my alocasia leaves are yellow, what should i change",                  # one question
    "my monstera is sending out aerial roots, what should i do? is that bad?",  # a 3-word tail is too thin to search
    "is it light or is it humidity",                                        # both halves too thin
])
def test_clauses_leave_a_single_question_whole(q):
    assert retrieve.clauses(q) == []


def _hit(cid):
    return retrieve.Hit(cid, f"text {cid}", "", "general", "t", 0.0)


def test_fuse_rewards_agreement_and_breaks_ties_by_first_seen():
    whole, part1, part2 = [_hit("a"), _hit("b"), _hit("c")], [_hit("b"), _hit("d")], [_hit("e"), _hit("a")]
    fused = retrieve.fuse([whole, part1, part2], k=4)
    # a and b tie at 1/61 + 1/62 (a seen first); then e 1/61 > d 1/62 > c 1/63
    assert [h.chunk_id for h in fused] == ["a", "b", "e", "d"]
    assert fused[0].content == "text a" and fused[0].score == pytest.approx(1 / 61 + 1 / 62)
    assert all(x.score >= y.score for x, y in zip(fused, fused[1:]))


def test_search_all_is_plain_search_for_one_query_and_fused_for_several(seeded):
    conn, emb = seeded
    one = retrieve.search_all(conn, ["alocasia spider mites"], [emb.embed_query("alocasia spider mites")], k=2)
    assert [(h.chunk_id, h.score) for h in one] == [(h.chunk_id, h.score) for h in retrieve.search(conn, emb, "alocasia spider mites", k=2)]
    qs = ["alocasia spider mites and quarantine", "alocasia spider mites", "quarantine new plants"]
    many = retrieve.search_all(conn, qs, [emb.embed_query(q) for q in qs], k=3)
    expected = retrieve.fuse([retrieve.search(conn, emb, q, k=retrieve.POOL) for q in qs], k=3)
    assert [h.chunk_id for h in many] == [h.chunk_id for h in expected]
