"""Eval question set: load, validate, and the fixed dev/holdout split.

  uv run python -m eval.questions      # give any row without a split one (seeded, stratified by category); existing splits never move
Validation against the live chunks table runs at the start of every `eval.run`.
"""
import json
import random
import re
from collections import Counter
from pathlib import Path

from rag.generate import MAX_QUESTION, REFUSAL

PATH = Path(__file__).with_name("questions.jsonl")
CATEGORIES = ("factual", "multi-hop", "oos-near", "oos-far")
SPLITS = ("dev", "holdout")
REQUIRED = ("id", "category", "must_refuse", "split", "question", "gold_answer", "gold_chunk_ids")
SEED, HOLDOUT_SHARE, SHINGLE = 20260924, 0.4, 10


def load(path: Path = PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(rows: list[dict], path: Path = PATH) -> None:
    order = REQUIRED + ("note",)
    keyed = ({**{k: r[k] for k in order if k in r}, **{k: v for k, v in r.items() if k not in order}} for r in rows)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keyed), encoding="utf-8")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _grams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def problems(rows: list[dict], chunk_ids: set[str], corpus_texts: list[str]) -> list[str]:
    """Every reason the set is unfit to run; empty means valid. `chunk_ids` comes from the live chunks table.
    Leakage: any SHINGLE-word run of a question in the corpus, or the whole question when it is shorter than that."""
    corpus, grams = [_tokens(t) for t in corpus_texts], {}

    def leaked(question: str) -> bool:
        t = _tokens(question)
        n = min(SHINGLE, len(t))
        if n and n not in grams:
            grams[n] = set().union(*(_grams(c, n) for c in corpus))
        return bool(n and _grams(t, n) & grams[n])

    out, seen = [], set()
    for r in rows:
        rid = r.get("id", "?")
        if rid in seen:
            out.append(f"{rid}: duplicate id")
        seen.add(rid)
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            out.append(f"{rid}: missing {', '.join(missing)}")
            continue
        gold = r["gold_chunk_ids"]
        checks = [
            (r["category"] not in CATEGORIES, f"unknown category {r['category']!r}"),
            (r["split"] not in SPLITS, f"unknown split {r['split']!r}"),
            (len(r["question"]) > MAX_QUESTION, f"question over {MAX_QUESTION} chars"),
            (r["gold_answer"].startswith("PENDING"), "gold answer still PENDING"),
            (r["must_refuse"] and (bool(gold) or r["gold_answer"] != REFUSAL), "must_refuse row needs no gold and the exact refusal answer"),
            (not r["must_refuse"] and (not gold or not all(gold)), "answerable row needs non-empty gold groups"),
            (leaked(r["question"]), f"leakage: the question (or a {SHINGLE}-word run of it) appears in the corpus"),
        ]
        out += [f"{rid}: {msg}" for bad, msg in checks if bad]
        out += [f"{rid}: gold chunk not in chunks table: {c}" for c in sorted({c for g in gold for c in g} - chunk_ids)]
    return out


def assign_split(rows: list[dict], seed: int = SEED, share: float = HOLDOUT_SHARE) -> None:
    """Seeded and stratified by category; only rows without a split are assigned, so an assignment never moves,
    and the holdout share is kept over the whole category as questions are added."""
    rng = random.Random(seed)
    for cat in CATEGORIES:
        in_cat = [r for r in rows if r["category"] == cat]
        todo = sorted((r for r in in_cat if "split" not in r), key=lambda r: r["id"])
        rng.shuffle(todo)
        cut = max(0, round(len(in_cat) * share) - sum(r.get("split") == "holdout" for r in in_cat))
        for i, r in enumerate(todo):
            r["split"] = "holdout" if i < cut else "dev"


if __name__ == "__main__":
    rows = load()
    assign_split(rows)
    save(rows)
    print(dict(Counter((r["split"], r["category"]) for r in rows)))
