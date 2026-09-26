# Punchlist — 2026-09-25 — Keegan's answers to the hardening round

Plan of record: `~/.claude/plans/ok-lets-plan-this-glistening-heron.md`. Yesterday: `2026-09-24-punchlist.md`.
A box is checked only when DONE with evidence pasted.

## Ledger

| step | tier | est tokens | actual |
|---|---|---|---|
| prompt v2 + inline-ids metric + v3 run + blind sheet | inline (single seam: prompt + one metric) | 40K | — |
| local-only docs, memory | inline | 10K | — |

## Ask 1 — "drop them and let the UI show the citation when we make it"

Diagnosis: prompt rule 2 asks for inline `[chunk_id]` markers and the model complies in about half the answers; the
validated `citations` list is the source the UI will render.

- [x] Metric first (TDD): `inline ids` = answered rows whose text holds a `[doc#section]` marker, in `grade.summarize`, the run report and `eval.table` → `a409128`: 3 tests red, then `24 passed`; full suite `173 passed`; v1.1 4/14, v2 6/14, v2.1 3/14
- [x] Prompt v2: rule 2 lists used chunk_ids in `citations` only and forbids ids, brackets or source markers in `answer`; one change vs prompt v1 → `3c70514`
- [x] v3 (prompt v2, v2's retrieval: vector, k=5, decompose) on dev; backend errors retried → `526ae40`: 23 rows, 0 backend errors, second pass ran 0
- [x] Verify: `inline ids` 0/14 for v3; `eval.gate v2.1 v3` passes (retrieval identical, 0 hallucination, 0 errors); citations per answer not lower than v2.1 → gate PASS (warns code_sha, sql_sha); inline ids 3/14 → 0/14. The citations criterion as written is NOT met (2.64 → 2.50): the two answers citing fewer sections (f09, f11) were read and every fact in them is in a cited section; they draw on fewer sections (median 128.5 → 113 words), so the count was the wrong proxy for completeness
- [x] Blind side-by-side sheet v2.1 vs v3 for Keegan, key held back → sent (scratchpad `pick-v2.1-v3-blind.md`, key `blind-key-v2.1-v3.json`); inline markers stripped from both answers so they can't unblind, spacing artifacts checked: 0
- [x] Architect verified: live `/ask` answer on the final code carries no markers and a non-empty validated `citations` list → :8014, m06-style question: readyz 200, `inline markers in answer: []`, 2 citations, all retrieved; server stopped

## Ask 2 — "Lets avoid an API for now keep it all local no need to spend yet, if at all."

- [x] README, status doc and memory: the demo runs locally on the `cc` backend; no API runs, no spend; the `api` backend code stays, tested with fakes only; Act 2 on the API is off (a free `cc`-backend variant is a question for Keegan) → `41048bb` (README 'Run it', contract §3 `ANTHROPIC_API_KEY` unused, status pointer); memory `plant-care-rag-project` updated with his words

## Ask 3 — "Im fine with just showing and demoing not necessarily providing access to everyone publicly."

- [x] README: no hosted endpoint; the container is a packaging artifact for a keyed deployment, not the demo path → `41048bb`

## Ask 4 — "Blind grading everything seems fine"

- [x] Memory: blind side-by-side is the standing grading method (update `keegan-grading-style`) → updated with his words

## Open at round end

Keegan's blind picks: m04/m06 (v1.1 vs v2, sent 2026-09-24) and 14 questions v2.1 vs v3 (sent 2026-09-25). Judge alignment still needs graded answers. GitHub push not yet asked for. Act 2, if any, on the `cc` backend.

## Ask 5 — "all correct on the generations as far as I can tell"

- [x] Recorded for the v2.1-vs-v3 sheet: 13 questions graded c for both versions (`eval/results/v2.1/grades.jsonl`, `eval/results/v3/grades.jsonl`), comparison 14 ties (`eval/results/comparisons/v2.1_vs_v3.jsonl`), `eval.compare v2.1 v3` → `v2.1 0 · v3 0 · tie 14 · sign test p = 1.0`; reports show `13 c, 0 p, 0 w, 1 ungraded`
- [ ] m04 grade: both answers say they have no feeding information (retrieval misses the first-watering section); his v0 grading counted that gap as partial, so asked, not assumed
- [ ] whether "all correct" also covers the m04/m06 v1.1-vs-v2 sheet (sent 2026-09-24): asked
