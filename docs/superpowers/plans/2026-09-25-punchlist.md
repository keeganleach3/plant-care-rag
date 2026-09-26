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

- [ ] Metric first (TDD): `inline ids` = answered rows whose text holds a `[doc#section]` marker, in `grade.summarize`, the run report and `eval.table`
- [ ] Prompt v2: rule 2 lists used chunk_ids in `citations` only and forbids ids, brackets or source markers in `answer`; one change vs prompt v1
- [ ] v3 (prompt v2, v2's retrieval: vector, k=5, decompose) on dev; backend errors retried
- [ ] Verify: `inline ids` 0/14 for v3; `eval.gate v2.1 v3` passes (retrieval identical, 0 hallucination, 0 errors); citations per answer not lower than v2.1
- [ ] Blind side-by-side sheet v2.1 vs v3 for Keegan, key held back
- [ ] Architect verified: live `/ask` answer on the final code carries no markers and a non-empty validated `citations` list

## Ask 2 — "Lets avoid an API for now keep it all local no need to spend yet, if at all."

- [ ] README, status doc and memory: the demo runs locally on the `cc` backend; no API runs, no spend; the `api` backend code stays, tested with fakes only; Act 2 on the API is off (a free `cc`-backend variant is a question for Keegan)

## Ask 3 — "Im fine with just showing and demoing not necessarily providing access to everyone publicly."

- [ ] README: no hosted endpoint; the container is a packaging artifact for a keyed deployment, not the demo path

## Ask 4 — "Blind grading everything seems fine"

- [ ] Memory: blind side-by-side is the standing grading method (update `keegan-grading-style`)

## Open at round end

<filled at the end>
