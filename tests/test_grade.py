"""Deterministic eval metrics (pure; no DB, no LLM)."""
from eval import grade as G


def res(ids=("a#1",), refused=False, error=None, total=100.0, gen=80.0):
    return {"chunks": [{"chunk_id": c} for c in ids], "refused": None if error else refused,
            "error": {"kind": error, "detail": "x"} if error else None,
            "timings": {"embed_ms": 10.0, "retrieve_ms": 10.0, "generate_ms": gen, "total_ms": total}}


REFUSE_Q = {"id": "n1", "category": "oos-near", "must_refuse": True, "gold_chunk_ids": []}
ANSWER_Q = {"id": "f1", "category": "factual", "must_refuse": False, "gold_chunk_ids": [["a#1"]]}


def test_recall_counts_a_fact_when_any_chunk_in_its_group_is_retrieved():
    assert G.recall_at_k([["a#1", "b#1"], ["c#1"]], ["b#1", "z#9"]) == 0.5
    assert G.recall_at_k([["a#1"]], []) == 0.0
    assert G.recall_at_k([], ["a#1"]) is None


def test_grade_refusal_outcomes():
    assert G.grade(REFUSE_Q, res(refused=False))["hallucinated"] is True
    assert G.grade(REFUSE_Q, res(refused=True))["hallucinated"] is False
    assert G.grade(ANSWER_Q, res(refused=True))["false_refusal"] is True
    assert G.grade(ANSWER_Q, res(refused=False))["false_refusal"] is False
    errored = G.grade(ANSWER_Q, res(error="citation_invalid"))
    assert (errored["false_refusal"], errored["error"], errored["recall"]) == (None, "citation_invalid", 1.0)


def test_summary_denominators_exclude_errors_from_rates_but_not_from_recall():
    qs = [ANSWER_Q, {**ANSWER_Q, "id": "f2", "gold_chunk_ids": [["b#1"]]}, {**ANSWER_Q, "id": "f3"}, REFUSE_Q, {**REFUSE_Q, "id": "n2"}]
    rs = [res(["a#1"], total=100), res(["z#1"], refused=True, total=300), res(["a#1"], error="timeout", total=120000),
          res([], refused=False, total=200), res([], error="cli_error", total=50)]
    s = G.summarize(list(zip(qs, rs)))
    assert s["n"] == 5 and s["errors"] == {"timeout": 1, "cli_error": 1}
    assert s["recall"] == (2 / 3, 3)            # f1 hit, f2 miss, f3 hit though generation failed
    assert s["false_refusal"] == (1, 2)         # f2 refused; f3 errored, so not counted
    assert s["hallucination"] == (1, 1)         # n1 answered; n2 errored
    assert s["timed"] == 3 and (s["p50_total_ms"], s["p95_total_ms"]) == (200.0, 290.0)  # latency over non-error rows only


def test_summary_of_nothing_applicable_has_a_zero_denominator():
    s = G.summarize([(ANSWER_Q, res())])
    assert s["hallucination"] == (0, 0)
