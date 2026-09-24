"""Eval runner: resume, retries, frozen config, holdout hygiene, report, and the main() gate (fake pipeline; no DB, no LLM)."""
import json
import re

import pytest

from eval import run as R

CONFIG = {"mode": "vector", "k": 5, "embed_model": "m", "llm_backend": "cc", "code_sha": "c", "chunks_sha": "c"}


def q(rid, **kw):
    return {"id": rid, "category": "factual", "must_refuse": False, "split": "dev", "question": f"question {rid}",
            "gold_answer": "A.", "gold_chunk_ids": [["a#1"]], **kw}


ROWS = [q("f1"), q("f2"), q("n1", category="oos-near", must_refuse=True, gold_chunk_ids=[])]


class FakeAsk:
    def __init__(self, error_on=(), kind="citation_invalid"):
        self.calls, self.error_on, self.kind = [], set(error_on), kind

    def __call__(self, question):
        self.calls.append(question)
        base = {"params": {"k": 5, "mode": "vector", "genus": None}, "chunks": [{"chunk_id": "a#1", "content": "x"}],
                "model": "claude-sonnet-5", "timings": {"embed_ms": 1.0, "retrieve_ms": 1.0, "generate_ms": 5.0, "total_ms": 7.0}}
        if question in self.error_on:
            return {**base, "error": {"kind": self.kind, "detail": "boom", "attempts": 1, "usage": None}}
        return {**base, "error": None, "answer": "A.", "citations": ["a#1"], "refused": False, "usage": {}}


def results(out_dir, name="results.jsonl"):
    return [json.loads(line) for line in (out_dir / name).read_text(encoding="utf-8").splitlines()]


def test_resume_reruns_exactly_the_deleted_row(tmp_path):
    ask = FakeAsk()
    assert R.run(tmp_path, ROWS, ask, CONFIG) == 3
    assert R.run(tmp_path, ROWS, ask, CONFIG) == 0
    kept = [r for r in results(tmp_path) if r["id"] != "f2"]
    (tmp_path / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in kept), encoding="utf-8")
    ask.calls.clear()
    assert R.run(tmp_path, ROWS, ask, CONFIG) == 1 and ask.calls == ["question f2"]


def test_changed_config_for_an_existing_version_aborts_before_any_call(tmp_path):
    R.run(tmp_path, ROWS, FakeAsk(), CONFIG)
    ask = FakeAsk()
    with pytest.raises(R.RunError, match=r"\(k\)"):
        R.run(tmp_path, ROWS + [q("f5")], ask, {**CONFIG, "k": 10})
    assert ask.calls == []


def test_reps_and_error_rows_are_recorded_with_their_kind(tmp_path):
    R.run(tmp_path, ROWS[:1], FakeAsk(error_on={"question f1"}), CONFIG, reps=2)
    rows = results(tmp_path)
    assert [(r["id"], r["rep"]) for r in rows] == [("f1", 1), ("f1", 2)]
    assert rows[0]["error"]["kind"] == "citation_invalid" and rows[0]["chunks"] and rows[0]["model"]
    assert "citation_invalid 2" in R.report(tmp_path, ROWS[:1])


def test_backend_errors_are_retried_and_the_latest_attempt_counts(tmp_path):
    R.run(tmp_path, ROWS[:1], FakeAsk(error_on={"question f1"}, kind="cli_error"), CONFIG)
    assert R.run(tmp_path, ROWS[:1], FakeAsk(), CONFIG) == 1
    assert [bool(r["error"]) for r in results(tmp_path)] == [True, False]  # append-only: the failed attempt stays as history
    assert "cli_error" not in R.report(tmp_path, ROWS[:1])
    R.run(tmp_path, ROWS[1:2], FakeAsk(error_on={"question f2"}), CONFIG)  # a rejected answer is a result, not a retry
    assert R.run(tmp_path, ROWS[1:2], FakeAsk(), CONFIG) == 0


def test_three_consecutive_backend_errors_stop_the_run(tmp_path):
    rows = [q(f"f{i}") for i in range(5)]
    with pytest.raises(R.RunError, match="3 consecutive cli_error"):
        R.run(tmp_path, rows, FakeAsk(error_on={r["question"] for r in rows}, kind="cli_error"), CONFIG)
    assert len(results(tmp_path)) == 3


def test_holdout_rows_never_reach_the_log_and_live_in_their_own_file(tmp_path):
    lines = []
    R.run(tmp_path, [q("f1"), q("h7", split="holdout")], FakeAsk(), CONFIG, log=lines.append)
    assert lines and not any("h7" in line for line in lines)
    assert [r["id"] for r in results(tmp_path)] == ["f1"]
    assert [r["id"] for r in results(tmp_path, "results.holdout.jsonl")] == ["h7"]


def test_report_has_no_blank_cells_and_shows_holdout_only_in_aggregate(tmp_path):
    rows = ROWS + [q("f9", split="holdout"), q("n9", split="holdout", category="oos-near", must_refuse=True, gold_chunk_ids=[])]
    R.run(tmp_path, rows, FakeAsk(), CONFIG)
    text = R.report(tmp_path, rows)
    assert (tmp_path / "report.md").read_text(encoding="utf-8") == text
    table = [line for line in text.splitlines() if line.startswith("|")]
    assert table and not any(re.search(r"\|\s*\|", line) or "None" in line for line in table)
    assert "| holdout | all |" in text and "| holdout | factual" not in text and "| holdout | oos-near" not in text
    assert "f9" not in text and "n9" not in text


def test_report_shows_manual_accuracy_from_the_grades_file(tmp_path):
    R.run(tmp_path, ROWS, FakeAsk(), CONFIG)
    (tmp_path / "grades.jsonl").write_text(json.dumps({"id": "f1", "rep": 1, "grade": "c", "unfaithful": False}) + "\n", encoding="utf-8")
    text = R.report(tmp_path, ROWS)
    assert "| dev | all | 3 |" in text and "1 c, 0 p, 0 w, 1 ungraded" in text and "0/1" in text and "narrates" in text


def test_report_on_a_version_that_never_ran_is_a_clear_error(tmp_path):
    with pytest.raises(R.RunError, match="no run"):
        R.report(tmp_path / "v9", ROWS)


class FakeConn:
    def __init__(self, chunk_ids):
        self.chunk_ids, self.rows = chunk_ids, []

    def execute(self, sql, params=None):
        self.rows = [("CREATE FUNCTION hybrid_search ...",)] if "pg_get_functiondef" in sql else \
            [(c, "general", "light", "md5-content", "md5-embedding") for c in self.chunk_ids]
        return self

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0]


def _patch_main(monkeypatch, tmp_path, rows, chunk_ids):
    fake = FakeAsk()
    monkeypatch.setattr(R.questions, "load", lambda *a: rows)
    monkeypatch.setattr(R, "RESULTS", tmp_path)
    monkeypatch.setattr(R, "settings", lambda: {"EMBED_MODEL": "m", "LLM_BACKEND": "cc"})
    monkeypatch.setattr(R.db, "connect", lambda: FakeConn(chunk_ids))
    monkeypatch.setattr(R, "Embedder", lambda name: None)
    monkeypatch.setattr(R.pipeline, "ask", lambda conn, emb, question, **kw: fake(question))
    return fake.calls


def test_main_refuses_on_a_bad_gold_id_before_any_call(tmp_path, monkeypatch):
    calls = _patch_main(monkeypatch, tmp_path, [q("f1", gold_chunk_ids=[["missing#x"]])], ["a#1"])
    with pytest.raises(SystemExit, match="missing#x"):
        R.main(["--version", "t"])
    assert calls == [] and not (tmp_path / "t").exists()


def test_main_runs_only_the_requested_split_and_freezes_everything_that_changes_results(tmp_path, monkeypatch):
    calls = _patch_main(monkeypatch, tmp_path, [q("f1"), q("f2", split="holdout")], ["a#1"])
    R.main(["--version", "t", "--k", "50"])
    assert calls == ["question f1"]
    cfg = json.loads((tmp_path / "t" / "config.json").read_text(encoding="utf-8"))
    assert cfg["k"] == 20 and set(cfg) == {"mode", "k", "embed_model", "llm_backend", "llm_model", "effort",
                                           "code_sha", "sql_sha", "chunks_sha", "questions_sha"}
