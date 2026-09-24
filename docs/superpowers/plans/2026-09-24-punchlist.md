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
- [x] 4.5 baseline v0 (vector, k=5, dev) recorded: recall@5 0.88 (n=14; factual 0.94, multi-hop 0.79), hallucination 0/9, false refusal 0/14, errors 0 (one transient empty-detail `cli_error` on f12, retried by the rerun: 1 call, answered), P50/P95 total 7.2 s / 26.2 s, generate-bound. Recall misses: m04 0.00 (two-part question; all 5 hits are dome sections, feeding never retrieved), f07 0.50, m10 0.75. Earlier attempt 2026-09-24: 23/23 `cli_error`, the `claude` CLI's saved OAuth token expired 2026-09-14 with no refresh token (env A/B ruled out session inheritance). Discarded (uncommitted, pre-review config). Keegan ran `claude auth login`: status `subscriptionType: max`, refresh token present, live probe cited `general-acclimation#humidity-hold-100-percent-for-the-first-week` via claude-sonnet-5. Rerun started.
- [x] Keegan's manual grades for the 14 answered v0 dev questions: 11 c, 3 p (f07 missing content, m04 retrieval miss, m10 missing content + answer voice), 0 w, 0 unfaithful → `eval/results/v0/grades.jsonl`; report gains accuracy + unfaithful columns (TDD, 59 tests)
- [x] his feedback applied: Alocasia 100% hold "about 15 to 20 days" + gradual acclimation into ambient; leaf-melt "base of the plant (not a leaf's stalk)"; S16 = Samsung LM301H EVO, 3.14 µmol/J PPE. Gold f06/f07/f08/m08 updated (f07 now one group, so v0 recall reads 0.91 instead of 0.88; its p grade stands)
- [x] Keegan verified the 3 edited docs (`2df5c0a`) and approved the S16 section (`12483da`): 42 W for a set of four, power scales with the level, 132/92/66 µmol/s at levels 10/7/5, area averages for 2×2 and 2×4 ft; chart figures labelled center-of-bar (his statement), S16 figures labelled estimates and area averages. m10 gold uses it
- [x] Docker died abruptly at 13:13 (log ends mid-stream); parked both socket folders, one launch: daemon 29.7.2, DB healthy. `rag.ingest --prune`: `22 docs, 96 chunks, pruned 0, skipped 0`; `pytest -q`: `61 passed`
- [x] "narrates" metric (`bde4d6c`): v0 3/14 answers talk about notes/passages
- [ ] v0.1 (new corpus, prompt v0) → then prompt v1 (humanizer-derived voice rules, drafted in scratch) committed → v1 → blind side-by-side sheet for Keegan (key held back)
- [ ] judge alignment (4.4) needs more graded answers: 14 grades with 0 w cannot calibrate a judge; accumulate grades across v0.1 and Phase 5 versions first
- Phase 5 queue, each only on a dev failure: prompt v1 answer voice (m10: no "the notes" mechanics in answers), multi-part query retrieval (m04), hybrid with an OR'd lexical leg (FTS 1/38)
- [ ] before judging hybrid in Phase 5: count how many of the 38 questions get ANY full-text match. `hybrid_search` uses `plainto_tsquery`, which ANDs every term, so full customer questions may never match (unverified; the 2026-09-10 sanity ranks were identical in both modes)
