"""Manual retrieval sanity check: 10 customer-voice queries with the chunk each should hit (Phase 2.1 verify).
  uv run python -m eval.sanity   → prints rank per mode, appends a dated block to eval/notes.md"""
from datetime import date
from pathlib import Path

from rag import db, retrieve
from rag.config import settings
from rag.embed import Embedder

CASES = [
    ("how humid should tc plants be when i first plant them", "general-acclimation#humidity-hold-100-percent-for-the-first-week"),
    ("my alocasia dropped all its leaves is it dead", "alocasia-acclimation#leaf-drop-during-alocasia-acclimation-is-normal"),
    ("thrips on my monstera what do i spray", "general-pests#thrips-rotate-sprays-every-four-days-or-use-systemic-granules"),
    ("black spots with rings on alocasia leaf", "alocasia-pests#leaf-spot-on-alocasia-what-it-looks-like"),
    ("my variegated monstera is going all green", "monstera-quirks#if-a-variegated-monstera-is-reverting-to-green"),
    ("what soil mix for tc anthurium", "general-substrate-water#first-substrate-mix-by-genus"),
    ("how long can i leave the tc bag unopened", "general-acclimation#unopened-bags-and-flasks-must-stay-below-75-f"),
    ("when should i repot", "general-acclimation#up-potting-wait-for-root-bound-do-not-disturb-the-roots"),
    ("caramel marble not growing", "philodendron-troubleshooting#slow-growth-on-philodendron-is-usually-normal"),
    ("how much light do variegated monsteras need", "general-light#established-plants-at-least-300-ppfd-for-12-to-14-hours"),
]


def main():
    conn = db.connect()
    emb = Embedder(settings()["EMBED_MODEL"])
    lines = [f"## Retrieval sanity — {date.today()} — {emb.name}", "", "| query | expected | vector rank | hybrid rank |", "|---|---|---|---|"]
    hits = {"vector": 0, "hybrid": 0}
    for q, want in CASES:
        ranks = {}
        for mode in ("vector", "hybrid"):
            ids = [h.chunk_id for h in retrieve.search(conn, emb, q, k=10, mode=mode)]
            ranks[mode] = ids.index(want) + 1 if want in ids else None
            hits[mode] += ranks[mode] is not None and ranks[mode] <= 5
        lines.append(f"| {q} | `{want}` | {ranks['vector'] or 'miss'} | {ranks['hybrid'] or 'miss'} |")
    lines += ["", f"top-5 hits: vector {hits['vector']}/{len(CASES)}, hybrid {hits['hybrid']}/{len(CASES)}", ""]
    out = "\n".join(lines)
    print(out)
    p = Path(__file__).with_name("notes.md")
    p.write_text((p.read_text(encoding="utf-8") if p.exists() else "# Retrieval notes\n\n") + out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
