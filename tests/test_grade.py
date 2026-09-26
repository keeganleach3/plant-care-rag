"""Deterministic eval metrics (pure; no DB, no LLM)."""
from eval import grade as G


def res(ids=("a#1",), refused=False, error=None, total=100.0, gen=80.0):
    return {"rep": 1, "answer": "About 150 PPFD.", "chunks": [{"chunk_id": c} for c in ids], "refused": None if error else refused,
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


def test_accuracy_takes_manual_grades_for_answers_and_scores_a_wrongful_refusal_as_wrong():
    qs = [ANSWER_Q, {**ANSWER_Q, "id": "f2"}, {**ANSWER_Q, "id": "f3"}, {**ANSWER_Q, "id": "f4"}, {**ANSWER_Q, "id": "f5"}, REFUSE_Q]
    rs = [res(), res(), res(refused=True), res(), res(error="timeout"), res(refused=True)]
    grades = {("f1", 1): {"grade": "c", "unfaithful": False}, ("f2", 1): {"grade": "p", "unfaithful": True}}
    s = G.summarize(list(zip(qs, rs)), grades)
    assert s["accuracy"] == {"c": 1, "p": 1, "w": 1, "ungraded": 1}  # f3 refused → w; f4 answered but ungraded; f5 errored
    assert s["unfaithful"] == (1, 2)


def test_narration_of_sources_is_caught_without_flagging_plain_answers():
    assert G.narrates("The notes don't give a PPFD for that light.") and G.narrates("Per the provided passages, hold 100%.")
    assert not G.narrates("Hold 100 percent for about 15 to 20 days [alocasia-acclimation#x], then step down slowly.")


def test_the_permitted_refusal_sentence_inside_a_partial_answer_is_not_narration():
    assert not G.narrates("Hold 100 percent for a week [a#x]. On feeding, I don't have information on that in my notes.")
    assert G.narrates("Hold 100 percent for a week [a#x]. My notes don't cover feeding.")


def test_summary_counts_narration_over_answered_rows_only():
    qs = [ANSWER_Q, {**ANSWER_Q, "id": "f2"}, {**ANSWER_Q, "id": "f3"}, REFUSE_Q]
    rs = [{**res(), "answer": "My notes say 150 PPFD."}, {**res(), "answer": "About 150 PPFD."},
          {**res(refused=True), "answer": "I don't have information on that in my notes."}, {**res(refused=True), "answer": "I don't have information on that in my notes."}]
    assert G.summarize(list(zip(qs, rs)))["narrates"] == (1, 2)


def test_summary_counts_answers_with_inline_chunk_ids_over_answered_rows():
    assert G.cites_inline("Hold 100 percent [general-acclimation#humidity-hold].") and not G.cites_inline("Hold 100 percent.")
    qs = [ANSWER_Q, {**ANSWER_Q, "id": "f2"}, REFUSE_Q]
    rs = [{**res(), "answer": "About 150 PPFD [general-light#x]."}, {**res(), "answer": "About 150 PPFD."},
          {**res(refused=True), "answer": "I don't have information on that in my notes."}]
    assert G.summarize(list(zip(qs, rs)))["inline_ids"] == (1, 2)


def test_summary_of_nothing_applicable_has_a_zero_denominator():
    s = G.summarize([(ANSWER_Q, res())])
    assert s["hallucination"] == (0, 0)
