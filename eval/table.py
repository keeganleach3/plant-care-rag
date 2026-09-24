"""Per-version results table for the README, rebuilt from the results files (dev split, latest attempt per row).

  uv run python -m eval.table v0 v0.1 v1 v1.1 v2
"""
import argparse

from eval import grade, questions
from eval.gate import _config, _pairs
from rag.config import RESULTS


def table(versions: list[str], rows: list[dict]) -> str:
    frac = lambda pair: f"{pair[0]}/{pair[1]}"
    lines = ["| version | k | n | recall@k | multi-hop recall@k | hallucination | false refusal | narrates | errors | P50 total s |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for v in versions:
        out_dir = RESULTS / v
        pairs = _pairs(out_dir, rows)
        s = grade.summarize(pairs)
        mh = grade.summarize([p for p in pairs if p[0]["category"] == "multi-hop"])
        lines.append(f"| {v} | {_config(out_dir).get('k', '—')} | {s['recall'][1]} | {s['recall'][0]:.2f} | "
                     f"{mh['recall'][0]:.2f} | {frac(s['hallucination'])} | {frac(s['false_refusal'])} | "
                     f"{frac(s['narrates'])} | {sum(s['errors'].values())} | {s['p50_total_ms'] / 1000:.1f} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("versions", nargs="+")
    print(table(ap.parse_args(argv).versions, questions.load()))


if __name__ == "__main__":
    main()
