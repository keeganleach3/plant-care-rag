"""Eval question set: validation gates and the fixed dev/holdout split (pure; no DB)."""
import random
from collections import Counter

from eval import questions as Q
from rag.chunker import chunk, parse
from rag.config import CORPUS
from rag.generate import REFUSAL

IDS = {"a#light", "b#light", "a#hours"}


def row(rid="f01", **kw):
    base = {"id": rid, "category": "factual", "must_refuse": False, "split": "dev", "question": "how much light for alocasia babies",
            "gold_answer": "About 150 PPFD.", "gold_chunk_ids": [["a#light", "b#light"], ["a#hours"]]}
    return {**base, **kw}


def test_valid_rows_have_no_problems():
    refuse = row("x01", category="oos-far", must_refuse=True, gold_answer=REFUSAL, gold_chunk_ids=[], question="who won the super bowl")
    assert Q.problems([row(), refuse], IDS, ["unrelated corpus text"]) == []


def test_gold_id_missing_from_chunks_is_a_problem():
    [p] = Q.problems([row()], IDS - {"a#hours"}, [])
    assert p.startswith("f01:") and "a#hours" in p


def test_question_shingle_found_in_corpus_is_leakage():
    q = "keep sealed plantlets below seventy five degrees or they will melt in the bag"
    [p] = Q.problems([row(question=q)], IDS, [f"Rule of thumb: {q.upper()}."])
    assert "leakage" in p


def test_short_question_found_whole_in_corpus_is_leakage():
    [p] = Q.problems([row(question="What should I use as fertilizer?")], IDS, ["Q: what should i use as fertilizer? A: 3-1-2."])
    assert "leakage" in p


def test_each_malformed_row_is_reported():
    bad = [
        row("n01", must_refuse=True, gold_answer=REFUSAL),                        # must_refuse but carries gold
        row("n02", must_refuse=True, gold_chunk_ids=[], gold_answer="Try this."),  # must_refuse without the refusal string
        row("f02", gold_chunk_ids=[]),                                             # answerable with no gold
        row("f03", gold_chunk_ids=[["a#light"], []]),                              # empty gold group
        row("f04", gold_answer="PENDING: ask Keegan"),
        row("f05", category="trivia"),
        row("f06", split="train"),
        row("f07", question="x" * 501),
    ]
    assert {p.split(":")[0] for p in Q.problems(bad, IDS, [])} == {r["id"] for r in bad}


def test_duplicate_id_and_missing_key_are_reported():
    no_split = row("f09")
    del no_split["split"]
    problems = Q.problems([row(), row(), no_split], IDS, [])
    assert any("duplicate" in p for p in problems) and any(p.startswith("f09:") and "split" in p for p in problems)


def test_assign_split_is_seeded_stratified_order_free_and_never_moves_an_assigned_row():
    rows = [row(f"f{i:02}") for i in range(13)] + [row(f"x{i}", category="oos-far") for i in range(5)]
    for r in rows:
        del r["split"]
    a, b = [dict(r) for r in rows], [dict(r) for r in rows]
    random.Random(1).shuffle(b)
    Q.assign_split(a)
    Q.assign_split(b)
    assert {r["id"]: r["split"] for r in a} == {r["id"]: r["split"] for r in b}
    holdout = Counter(r["category"] for r in a if r["split"] == "holdout")
    assert holdout == {"factual": 5, "oos-far": 2}  # round(0.4 × n) per category
    a[0]["split"] = "dev" if a[0]["split"] == "holdout" else "holdout"
    before = [r["split"] for r in a]
    Q.assign_split(a)
    assert [r["split"] for r in a] == before


def test_holdout_share_holds_as_questions_are_added_one_at_a_time():
    rows = []
    for i in range(10):
        rows.append(row(f"f{i:02}"))
        del rows[-1]["split"]
        Q.assign_split(rows)
    assert sum(r["split"] == "holdout" for r in rows) == 4


def test_save_keeps_keys_it_does_not_know(tmp_path):
    p = tmp_path / "q.jsonl"
    Q.save([row(extra=1)], p)
    assert Q.load(p)[0]["extra"] == 1


def test_real_question_set_is_well_formed():
    rows = Q.load()
    chunk_ids = {c.chunk_id for p in CORPUS.glob("*.md") if not p.name.startswith("_") for c in chunk(parse(p))}
    corpus = [p.read_text(encoding="utf-8") for p in CORPUS.glob("*.md")]
    assert Q.problems(rows, chunk_ids, corpus) == []
    assert Counter(r["category"] for r in rows) == {"factual": 13, "multi-hop": 10, "oos-near": 10, "oos-far": 5}
    assert Counter(r["split"] for r in rows) == {"dev": 23, "holdout": 15}
