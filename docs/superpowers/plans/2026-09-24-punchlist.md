# Punchlist — plant-care-rag, Phase 4 (eval set → harness)

Plan of record: `~/.claude/plans/ok-lets-plan-this-glistening-heron.md`. Contract: `docs/design/contract-pipeline.md` (eval-questions boundary row).
A box is checked only when DONE and verified with pasted output.

## 4.1a Gold mapping for Keegan's 38 questions (2026-09-24)
- [x] `eval/questions.jsonl`: question text verbatim, categories as given (13/10/10/5), gold answers and gold chunk groups drawn from corpus text only (`8887d47`)
- [x] verify (scratch check): `rows 38 · factual 13, multi-hop 10, oos-near 10, oos-far 5 · must_refuse 15 · pending [m09] · distinct gold ids 36 · errors: none`; mutation test caught all 3 planted defects (bad id, leaked shingle, gold on a must_refuse row)
- [x] `eval/sanity.py` expected ID follows the heading rename (`f59999d`); `pytest -q` → 18 passed, 12 skipped (Docker down)
- [x] review sheet sent to Keegan; open decisions listed
- [ ] GATE: Keegan confirms gold per row; edits applied; PENDING rows resolved
- ledger: `| 4.1a | inline (COMPLEX: a wrong gold row silently corrupts every metric) | 45K | — |`

## 4.1b After confirmation and the verified pass
- [ ] Keegan's verified pass: 4 unverified docs + sections changed since his last pass → `uv run python -m rag.ingest --prune` → chunk count pasted
- [ ] questions loader/validator, TDD: gold IDs must exist in `chunks`, leakage check, PENDING rejected, recall over any-of gold groups (if approved)
- [ ] seeded, category-stratified dev/holdout split
- [ ] then 4.2 grade.py, 4.3 run.py, 4.5 baseline v0
- [ ] before judging hybrid in Phase 5: count how many of the 38 questions get ANY full-text match. `hybrid_search` uses `plainto_tsquery`, which ANDs every term, so full customer questions may never match (unverified; the 2026-09-10 sanity ranks were identical in both modes)
