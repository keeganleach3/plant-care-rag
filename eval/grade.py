"""Deterministic eval metrics. Answer accuracy and citation faithfulness are graded separately (manual first, then a judge)."""
import re
import statistics
from collections import Counter

from rag.generate import INLINE_CITATION, REFUSAL

# An answer that talks about its own retrieval ("the notes say", "the passages") instead of about the plant. The exact
# refusal sentence is the one mention the prompt allows, including for the part of a question retrieval missed.
_NARRATION = re.compile(r"\b(?:my|the|these) notes\b|\bpassages?\b|\bprovided (?:text|context|information|sources?)\b", re.I)


def cites_inline(answer: str) -> bool:
    """A `[doc#section]` marker in the answer text; since prompt v2 the citations list is the only place for them."""
    return bool(INLINE_CITATION.search(answer))


def narrates(answer: str) -> bool:
    return bool(_NARRATION.search(answer.replace(REFUSAL, "")))


def recall_at_k(gold_groups: list[list[str]], retrieved: list[str]) -> float | None:
    """Share of required facts with at least one of their chunks retrieved; None when the row requires none."""
    if not gold_groups:
        return None
    got = set(retrieved)
    return sum(bool(got & set(g)) for g in gold_groups) / len(gold_groups)


def grade(q: dict, res: dict) -> dict:
    """One results row. A generation error leaves refusal outcomes undefined, but retrieval (and so recall) still happened."""
    refused = None if res["error"] else res["refused"]
    return {
        "recall": recall_at_k(q["gold_chunk_ids"], [c["chunk_id"] for c in res["chunks"]]),
        "hallucinated": None if refused is None or not q["must_refuse"] else not refused,
        "false_refusal": None if refused is None or q["must_refuse"] else refused,
        "error": res["error"]["kind"] if res["error"] else None,
    }


def _p95(values: list[float]) -> float:
    return values[0] if len(values) == 1 else statistics.quantiles(values, n=20, method="inclusive")[-1]


def _accuracy(pairs: list[tuple[dict, dict]], grades: dict) -> tuple[dict, tuple[int, int]]:
    """Answerable, non-error rows only: an answer takes Keegan's manual grade (c/p/w), a refusal is wrong, an answer
    he has not graded is counted as ungraded. Returns the counts and (unfaithful marks, graded answers)."""
    acc, marks = Counter(), []
    for q, r in pairs:
        if q["must_refuse"] or r["error"]:
            continue
        m = grades.get((q["id"], r["rep"]))
        acc["w" if r["refused"] else m["grade"] if m else "ungraded"] += 1
        if m and not r["refused"]:
            marks.append(bool(m.get("unfaithful")))
    return dict(acc), (sum(marks), len(marks))


def summarize(pairs: list[tuple[dict, dict]], grades: dict | None = None) -> dict:
    """Rates come back as (hits, denominator) so small-n results stay visible; latency covers the `timed` non-error rows.
    `grades` maps (id, rep) to a manual grade row."""
    graded = [(r, grade(q, r)) for q, r in pairs]
    recalls = [g["recall"] for _, g in graded if g["recall"] is not None]

    def count(key):
        flags = [g[key] for _, g in graded if g[key] is not None]
        return sum(flags), len(flags)

    out = {
        "n": len(graded),
        "errors": dict(Counter(g["error"] for _, g in graded if g["error"])),
        "recall": (statistics.fmean(recalls) if recalls else None, len(recalls)),
        "hallucination": count("hallucinated"),
        "false_refusal": count("false_refusal"),
    }
    out["accuracy"], out["unfaithful"] = _accuracy(pairs, grades or {})
    answered = [r for r, g in graded if not g["error"] and not r["refused"]]
    out["narrates"] = (sum(narrates(r["answer"]) for r in answered), len(answered))
    out["inline_ids"] = (sum(cites_inline(r["answer"]) for r in answered), len(answered))
    timed = [r["timings"] for r, g in graded if not g["error"]]
    out["timed"] = len(timed)
    for stage in ("total", "generate"):
        vals = [t[f"{stage}_ms"] for t in timed]
        out[f"p50_{stage}_ms"] = statistics.median(vals) if vals else None
        out[f"p95_{stage}_ms"] = _p95(vals) if vals else None
    return out
