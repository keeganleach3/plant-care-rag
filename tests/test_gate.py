"""Pure table tests: synthetic results rows written to tmp_path, no DB, no LLM."""
import json

from eval import gate

CATEGORIES = ("factual", "multi-hop", "oos-near", "oos-far")


def _q(id, category, *, must_refuse=False, gold=()):
    return {"id": id, "category": category, "must_refuse": must_refuse, "split": "dev",
            "question": id, "gold_answer": "x" if not must_refuse else "I don't have information on that in my notes.",
            "gold_chunk_ids": list(gold)}


def _row(id, *, chunks=(), error=None, refused=False, answer="ok"):
    row = {"id": id, "rep": 1, "chunks": [{"chunk_id": c} for c in chunks], "model": "claude-sonnet-5",
           "error": error, "timings": {"total_ms": 100.0, "generate_ms": 50.0}}
    if error is None:
        row |= {"answer": answer, "citations": list(chunks), "refused": refused, "usage": {}}
    return row


def _write(dir_, rows, config=None):
    """config=None writes `{}` (a run always has *a* config.json); config=False skips writing one, to simulate a
    missing/never-run directory."""
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    if config is not False:
        (dir_ / "config.json").write_text(json.dumps(config or {}), encoding="utf-8")


def test_candidate_errors_fail(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]])]
    _write(tmp_path / "base", [_row("f1", chunks=["a1"])])
    _write(tmp_path / "cand", [_row("f1", chunks=["a1"], error={"kind": "timeout", "detail": "boom", "attempts": 3, "usage": None})])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert any("errors" in l for l in lines)


def test_hallucination_fails(tmp_path):
    rows = [_q("o1", "oos-near", must_refuse=True)]
    _write(tmp_path / "base", [_row("o1", refused=True, answer="I don't have information on that in my notes.")])
    _write(tmp_path / "cand", [_row("o1", refused=False, answer="made up care advice")])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert any("hallucination" in l for l in lines)


def test_false_refusal_worse_than_baseline_fails(tmp_path):
    rows = [_q("f3", "factual", gold=[["e1"]])]
    _write(tmp_path / "base", [_row("f3", chunks=["e1"], refused=False, answer="the answer")])
    _write(tmp_path / "cand", [_row("f3", chunks=["e1"], refused=True, answer="I don't have information on that in my notes.")])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert any("false refusal" in l for l in lines)


def test_recall_drop_overall_fails(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]])]
    _write(tmp_path / "base", [_row("f1", chunks=["a1"])])
    _write(tmp_path / "cand", [_row("f1", chunks=["zzz"])])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert any("recall[all]" in l for l in lines)


def test_recall_drop_per_category_fails_even_when_overall_ties(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"], ["a2"]]), _q("f2", "factual", gold=[["b1"], ["b2"]]),
            _q("m1", "multi-hop", gold=[["c1"], ["c2"]]), _q("m2", "multi-hop", gold=[["d1"], ["d2"]])]
    _write(tmp_path / "base", [_row("f1", chunks=["a1"]), _row("f2", chunks=["b1"]),
                                _row("m1", chunks=["c1", "c2"]), _row("m2", chunks=["d1", "d2"])])
    _write(tmp_path / "cand", [_row("f1", chunks=["a1", "a2"]), _row("f2", chunks=["b1", "b2"]),
                                _row("m1", chunks=["c1"]), _row("m2", chunks=["d1"])])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert not any("recall[all]" in l for l in lines)          # 0.75 == 0.75, ties
    assert any("recall[multi-hop]" in l for l in lines)         # 1.00 -> 0.50, drops


def test_sha_mismatch_warns_but_does_not_fail(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]])]
    _write(tmp_path / "base", [_row("f1", chunks=["a1"])], config={"questions_sha": "aaa", "chunks_sha": "111"})
    _write(tmp_path / "cand", [_row("f1", chunks=["a1"])], config={"questions_sha": "bbb", "chunks_sha": "111"})
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 0
    assert any("questions_sha" in l and "warning" in l.lower() for l in lines)


def test_missing_config_json_fails(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]])]
    _write(tmp_path / "base", [_row("f1", chunks=["a1"])], config=False)
    _write(tmp_path / "cand", [_row("f1", chunks=["a1"])])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert any("config.json" in l and "base" in l for l in lines)


def test_missing_rows_fails(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]])]
    _write(tmp_path / "base", [])
    _write(tmp_path / "cand", [_row("f1", chunks=["a1"])])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert any("no dev rows" in l and "base" in l for l in lines)


def test_id_rep_set_mismatch_fails_and_names_counts_and_ids(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]]), _q("m1", "multi-hop", gold=[["b1"]])]
    _write(tmp_path / "base", [_row("f1", chunks=["a1"]), _row("m1", chunks=["b1"])])
    _write(tmp_path / "cand", [_row("f1", chunks=["a1"])])
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 1
    assert any("baseline 2" in l and "candidate 1" in l for l in lines)
    assert any("m1" in l for l in lines)


def test_all_differing_config_keys_warn_with_arrow_format(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]])]
    _write(tmp_path / "base", [_row("f1", chunks=["a1"])], config={"mode": "vector", "llm_model": "claude-sonnet-5", "k": 5})
    _write(tmp_path / "cand", [_row("f1", chunks=["a1"])], config={"mode": "hybrid", "llm_model": "claude-opus-5", "k": 5})
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 0
    assert "warning: mode: vector → hybrid" in lines
    assert "warning: llm_model: claude-sonnet-5 → claude-opus-5" in lines
    assert not any(l.startswith("warning: k") for l in lines)


def test_clean_candidate_passes(tmp_path):
    rows = [_q("f1", "factual", gold=[["a1"]]), _q("o1", "oos-near", must_refuse=True)]
    base = [_row("f1", chunks=["a1"]), _row("o1", refused=True, answer="I don't have information on that in my notes.")]
    _write(tmp_path / "base", base)
    _write(tmp_path / "cand", base)
    code, lines = gate.evaluate(tmp_path / "base", tmp_path / "cand", rows)
    assert code == 0
    assert any("pass" in l.lower() for l in lines)
