# Punchlist — plant-care-rag, Phase 4 (eval set → harness)

Plan of record: `~/.claude/plans/ok-lets-plan-this-glistening-heron.md`. Contract: `docs/design/contract-pipeline.md` (eval-questions boundary row).
A box is checked only when DONE and verified with pasted output.

## 4.1a Gold mapping for Keegan's 38 questions (2026-09-24)
- [x] `eval/questions.jsonl`: question text verbatim, categories as given (13/10/10/5), gold answers and gold chunk groups drawn from corpus text only (`8887d47`)
- [x] verify (scratch check): `rows 38 · factual 13, multi-hop 10, oos-near 10, oos-far 5 · must_refuse 15 · pending [m09] · distinct gold ids 36 · errors: none`; mutation test caught all 3 planted defects (bad id, leaked shingle, gold on a must_refuse row)
- [x] `eval/sanity.py` expected ID follows the heading rename (`f59999d`); `pytest -q` → 18 passed, 12 skipped (Docker down)
- [x] review sheet sent to Keegan; open decisions listed
- [x] GATE: Keegan confirmed gold 2026-09-24 (any-of groups "yes"; f06/f09/m04/m05/m09 answers applied as corpus sections + gold; n08 partial answer); `a5ab3c8`, `2c40251`; check: 38 rows, 0 pending, 37 gold IDs resolve, no leakage
- ledger: `| 4.1a | inline (COMPLEX: a wrong gold row silently corrupts every metric) | 45K | — |`

## 4.1b Keegan's read-through (gate for any DB run)
- [x] every doc holding text he has not read set to `verified: false` (9 docs); reading list of the 38 new/changed sections sent
- [x] Keegan 2026-09-24: "verified everything as of now" → 9 flags flipped (`927e320`) → `rag.ingest --prune`: `ingested 22 docs, 95 chunks, pruned 2, skipped 0` → `eval.sanity`: top-5 vector 9/10, hybrid 9/10 (reverting-to-green miss now rank 7) → gate against live `chunks`: `gate problems: none`
- [x] FTS match-rate check (queued item below, done early): the `plainto_tsquery` leg matches ≥1 chunk for 1 of 38 questions (f03 only), so current hybrid ≡ vector on 37/38. v1 hybrid must OR the lexemes first or it compares vector with itself.

## 4.2–4.3 Harness (TDD; built while Keegan reads)
- [x] `rag/pipeline.py`: embed → retrieve → generate shared by `/ask` and the runner; a generation error returns chunks + timings + requested model + `error{kind, detail, attempts, usage}`; `/ask` key set pinned by test, 502 on error
- [x] `eval/questions.py`: load, `problems()` (keys, categories, split, must_refuse/gold consistency, PENDING, gold IDs ∈ chunks, leakage on 10-word runs or the whole question if shorter), `assign_split()` seeded, stratified, order-free, keeps 40% per category as rows are added, never moves an assigned row
- [x] split written into `questions.jsonl`: 23 dev / 15 holdout (5/4/4/2 holdout per category)
- [x] `eval/grade.py`: recall@k over any-of groups; hallucination over non-error must-refuse rows, false refusal over non-error answerable rows, errors counted by kind; P50/P95 over timed rows with the count shown
- [x] `eval/run.py`: validation gate before any call; `config.json` freezes mode, k (clamped), embed model, backend, LLM model, effort, code/SQL/chunks/questions hashes; append-only results, latest attempt per (id, rep) counts, backend errors (cli_error, timeout) retried on rerun, 3 in a row stop the run; holdout rows in `results.holdout.jsonl`, never logged by id, reported only as the overall row
- [x] review (reviewer, opus): 1 blocker + 9 major + 23 minor. Fixed B1, M1–M9, m1, m3, m6, m7, m9–m23. Deferred: m2 truncated final line (one buffered write per row, Ctrl-C cannot split it; revisit if seen), m4 non-LLMError exceptions escaping `llm.py` (predates this change; Phase 6 hardening), m5 per-row cost (derivable from usage × model × PRICES; Act 2)
- [x] verify: `pytest -q` → `57 passed` with Docker up; live gate refused on the pre-read-through DB (38 missing gold chunks, 0 calls, no results dir)
- [ ] 4.5 baseline v0 (vector, k=5, dev). First attempt 2026-09-24: 23/23 `cli_error`, the `claude` CLI's saved OAuth token expired 2026-09-14 with no refresh token (env A/B ruled out session inheritance). Discarded (uncommitted, pre-review config). Blocked on Keegan: `claude auth login`
- [ ] Keegan's manual accuracy grades for v0 dev answers (sheet generator ready in scratch)
- [ ] before judging hybrid in Phase 5: count how many of the 38 questions get ANY full-text match. `hybrid_search` uses `plainto_tsquery`, which ANDs every term, so full customer questions may never match (unverified; the 2026-09-10 sanity ranks were identical in both modes)
