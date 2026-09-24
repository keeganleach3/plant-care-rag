# v2.1 — v2's config on the hardened code (no-regression check)

Change: none to retrieval or the prompt. Same config as v2 (vector, k=5, decompose) on the code after the production
hardening round: typed backend errors, the rate-limit retry fix, the connection pool and serving guards, the
`embed_model` column, and hybrid's OR'd full-text leg (unused in vector mode).
Why: the hardening changed `rag/*.py`, so the served config is re-measured before anyone relies on it.
Result: `uv run python -m eval.gate v2 v2.1` passes; recall is identical overall and per category, 0 errors,
hallucinations or false refusals. Two `error_max_structured_output_retries` backend errors on the first pass were
retried (see [../../notes.md](../../notes.md)). Numbers: [report.md](report.md).
