"""README results table: every cell comes from the results files (no DB, no LLM)."""
from eval import table
from tests.test_gate import _q, _row, _write

REFUSAL = "I don't have information on that in my notes."


def test_table_rows_are_computed_from_each_versions_results(tmp_path, monkeypatch):
    monkeypatch.setattr(table, "RESULTS", tmp_path)
    rows = [_q("f1", "factual", gold=[["a1"]]), _q("m1", "multi-hop", gold=[["b1"], ["b2"]]), _q("o1", "oos-far", must_refuse=True)]
    _write(tmp_path / "va", [_row("f1", chunks=["a1"]), _row("m1", chunks=["b1"], answer="The notes say b."),
                             _row("o1", refused=True, answer=REFUSAL)], config={"k": 5})
    _write(tmp_path / "vb", [_row("f1", chunks=["a1"]), _row("m1", chunks=["b1", "b2"]), _row("o1", answer="Sure, marinate it.")], config={"k": 8})
    lines = table.table(["va", "vb"], rows).splitlines()
    assert lines[0].startswith("| version | k | n | recall@k | multi-hop recall@k | hallucination | false refusal | narrates | errors |")
    assert lines[2] == "| va | 5 | 2 | 0.75 | 0.50 | 0/1 | 0/2 | 1/2 | 0 | 0.1 |"
    assert lines[3] == "| vb | 8 | 2 | 1.00 | 1.00 | 1/1 | 0/2 | 0/3 | 0 | 0.1 |"
