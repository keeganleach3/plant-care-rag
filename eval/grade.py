"""Deterministic eval metrics. Answer accuracy and citation faithfulness are graded separately (manual first, then a judge)."""
import statistics
from collections import Counter


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


def summarize(pairs: list[tuple[dict, dict]]) -> dict:
    """Rates come back as (hits, denominator) so small-n results stay visible; latency covers the `timed` non-error rows."""
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
    timed = [r["timings"] for r, g in graded if not g["error"]]
    out["timed"] = len(timed)
    for stage in ("total", "generate"):
        vals = [t[f"{stage}_ms"] for t in timed]
        out[f"p50_{stage}_ms"] = statistics.median(vals) if vals else None
        out[f"p95_{stage}_ms"] = _p95(vals) if vals else None
    return out
