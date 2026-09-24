# Punchlist — plant-care-rag, Phase 4 (eval set → harness)

Plan of record: `~/.claude/plans/ok-lets-plan-this-glistening-heron.md`. Contract: `docs/design/contract-pipeline.md` (eval-questions boundary row).
A box is checked only when DONE and verified with pasted output.

## 4.1a Gold mapping for Keegan's 38 questions (2026-09-24)
- [ ] `eval/questions.jsonl`: question text verbatim, categories as given (13/10/10/5), gold answers and gold chunk groups drawn from corpus text only
- [ ] verify (scratch check): 38 rows, required keys, unique ids, category counts, must_refuse rows carry the exact refusal string and no gold, every gold ID resolves to a current corpus heading, leakage clean (no 10-word question shingle in corpus)
- [ ] `eval/sanity.py` expected ID follows the heading rename (`...-300-ppfd-...` → `...-250-ppfd-...`)
- [ ] review sheet sent to Keegan; open decisions listed
- [ ] GATE: Keegan confirms gold per row; edits applied; PENDING rows resolved
- ledger: `| 4.1a | inline (COMPLEX: a wrong gold row silently corrupts every metric) | 45K | — |`

## 4.1b After confirmation and the verified pass
- [ ] Keegan's verified pass: 4 unverified docs + sections changed since his last pass → `uv run python -m rag.ingest --prune` → chunk count pasted
- [ ] questions loader/validator, TDD: gold IDs must exist in `chunks`, leakage check, PENDING rejected, recall over any-of gold groups (if approved)
- [ ] seeded, category-stratified dev/holdout split
- [ ] then 4.2 grade.py, 4.3 run.py, 4.5 baseline v0
