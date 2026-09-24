"""Gate a candidate eval run against a baseline. Dev split only, latest attempt per (id, rep).

  uv run python -m eval.gate <baseline> <candidate>
Exit 1 with one line per failed rule: candidate errors > 0; hallucination hits > 0; false refusal count
> baseline; recall mean < baseline (overall or any category). Prints a pass table otherwise. Warns (no
fail) when the two runs' questions_sha or chunks_sha differ.
"""
import argparse
import json
import sys
from pathlib import Path

from eval import grade, questions
from eval.run import _latest
from rag.config import RESULTS

CATS = ("all",) + questions.CATEGORIES


def _pairs(out_dir: Path, rows: list[dict]) -> list[tuple[dict, dict]]:
    by_id = {r["id"]: r for r in rows if r["split"] == "dev"}
    return [(by_id[r["id"]], r) for r in _latest(out_dir).values() if r["id"] in by_id]


def _config(out_dir: Path) -> dict:
    p = out_dir / "config.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _summaries(out_dir: Path, rows: list[dict]) -> dict:
    pairs = _pairs(out_dir, rows)
    return {cat: grade.summarize([p for p in pairs if cat == "all" or p[0]["category"] == cat]) for cat in CATS}


def evaluate(baseline_dir: Path, candidate_dir: Path, rows: list[dict]) -> tuple[int, list[str]]:
    base, cand = _summaries(baseline_dir, rows), _summaries(candidate_dir, rows)
    fails = []

    cand_errors = cand["all"]["errors"]
    if cand_errors:
        fails.append(f"candidate errors > 0: {sum(cand_errors.values())} ({', '.join(f'{k} {v}' for k, v in sorted(cand_errors.items()))})")

    hallu, _ = cand["all"]["hallucination"]
    if hallu:
        fails.append(f"hallucination hits > 0: {hallu}")

    cand_fr, _ = cand["all"]["false_refusal"]
    base_fr, _ = base["all"]["false_refusal"]
    if cand_fr > base_fr:
        fails.append(f"false refusal {cand_fr} > baseline {base_fr}")

    for cat in CATS:
        cand_recall, _ = cand[cat]["recall"]
        base_recall, _ = base[cat]["recall"]
        if cand_recall is not None and base_recall is not None and cand_recall < base_recall:
            fails.append(f"recall[{cat}] {cand_recall:.2f} < baseline {base_recall:.2f}")

    lines = []
    base_cfg, cand_cfg = _config(baseline_dir), _config(candidate_dir)
    for key in ("questions_sha", "chunks_sha"):
        if base_cfg.get(key) != cand_cfg.get(key):
            lines.append(f"warning: {key} differs (baseline {base_cfg.get(key)}, candidate {cand_cfg.get(key)})")

    if fails:
        return 1, lines + fails

    lines.append("PASS")
    lines.append("| category | n | recall base | recall cand | errors | hallucination | false refusal |")
    lines.append("|---|---|---|---|---|---|---|")
    for cat in CATS:
        b, c = base[cat], cand[cat]
        fmt = lambda pair: "—" if pair[1] == 0 else f"{pair[0]:.2f}"
        lines.append(f"| {cat} | {c['n']} | {fmt(b['recall'])} | {fmt(c['recall'])} | "
                     f"{sum(c['errors'].values())} | {c['hallucination'][0]} | {c['false_refusal'][0]} |")
    return 0, lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("candidate")
    args = ap.parse_args(argv)
    code, lines = evaluate(RESULTS / args.baseline, RESULTS / args.candidate, questions.load())
    print("\n".join(lines))
    sys.exit(code)


if __name__ == "__main__":
    main()
