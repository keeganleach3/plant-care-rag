"""Blind pairwise comparisons between two eval versions: Keegan picks the better answer per question.

  uv run python -m eval.compare v0.1 v1        # win counts and an exact two-sided sign test (ties excluded)
Picks live in eval/results/comparisons/<a>_vs_<b>.jsonl: one row per question with the shown order, his pick, the winner, his note.
"""
import argparse
import json
from math import comb

from rag.config import RESULTS


def sign_test(wins: int, n: int) -> float:
    """Exact two-sided sign test: chance of a split at least this lopsided if neither version were better."""
    tail = sum(comb(n, k) for k in range(max(wins, n - wins), n + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summary(rows: list[dict], a: str, b: str) -> dict:
    wins = {v: sum(r["winner"] == v for r in rows) for v in (a, b, "tie")}
    return {**wins, "p": round(sign_test(wins[a], wins[a] + wins[b]), 4)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    args = ap.parse_args(argv)
    path = RESULTS / "comparisons" / f"{args.a}_vs_{args.b}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    s = summary(rows, args.a, args.b)
    print(f"{args.a} {s[args.a]} · {args.b} {s[args.b]} · tie {s['tie']} · sign test p = {s['p']} (n = {len(rows)})")


if __name__ == "__main__":
    main()
