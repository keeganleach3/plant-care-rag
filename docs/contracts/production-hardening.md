# Contract — production hardening of the served path (2026-09-24)

Keegan, 2026-09-24: "if there is other improvements you can start implementing to create a fantastic example of building a rag system that would survive a top level production environment without my approval starting working on those as well." Standing approval for this round; he reviews the result, not this page. Each item names the failure it prevents; nothing ships that prevents none.

## 1. Blast radius

Data touched: `chunks` (one new column, backfilled), `documents` (read only), both in the local Docker Postgres; the throwaway `plantcare_test*` databases.
Users affected: anyone who runs the API, and Keegan's Anthropic bill once Act 2 puts an API key behind `/ask`.
Worst case if wrong: an exposed `/ask` with no key check lets anyone spend Keegan's API budget; a silent embedding-model mismatch serves confident wrong care advice with no error anywhere; a mislabelled eval run puts false numbers in a public README.
Does not hit: `corpus/*.md` (source of truth, untouched), `prompts/*` (answer behaviour is out of scope, eval-gated separately), `eval/questions.jsonl` and every committed `eval/results/*` row, Keegan's `claude` login.
Areas touched: `rag/llm.py`, `rag/api.py`, `rag/db.py`, `rag/ingest.py`, `rag/config.py` — live · `db/init/*.sql` — live (fresh installs) · `eval/run.py` — live · `app/` — ghost (chat UI, not wired; not touched).

## 2. Trust boundaries

| Input enters at | Validated by (at that boundary) |
|---|---|
| `Authorization` header on `/ask` | when `API_KEY` is set: `Bearer <key>` compared with `hmac.compare_digest`, 401 otherwise; unset: startup logs a warning that `/ask` is open |
| `X-Request-ID` header | accepted only if it matches `^[A-Za-z0-9._-]{1,64}$`, else a fresh uuid4; echoed on the response |
| Request body | unchanged pydantic model (question 1–500 chars, `mode` enum, `k` clamped 1–20, `genus` ∈ GENERA or dropped, `decompose` bool) |
| `claude -p` stdout/stderr and exit code | every failure path → `LLMError(kind)` with the existing kinds only (the runner retries `cli_error`/`timeout`): `cli_error` (CLI missing from PATH, non-zero exit, `is_error`; detail = CLI `subtype`, exit code, stderr tail ≤ 500 chars), `timeout`, `schema_invalid` (unparseable JSON included), `model_mismatch`, `refusal` |
| Anthropic SDK response / exceptions | connection errors, timeouts and 5xx → retried by our loop only (SDK `max_retries=0`); non-JSON or missing text block → `schema_invalid` |
| Ingested vectors vs query vectors | `chunks.embed_model` written by ingest; the API's readiness and the eval runner refuse unless `{embed_model in chunks} == {EMBED_MODEL}` |

## 3. Data & secrets inventory

| Table | RLS posture |
|---|---|
| `documents`, `chunks` | no RLS by design: single-tenant public corpus, every row readable by the app, no per-user rows (contract-pipeline §3). Least-privilege app role is deferred (named in Open). |

Secrets: `API_KEY` (new, optional) in `.env` / container env, never logged, never echoed. `ANTHROPIC_API_KEY` unchanged (Keegan pastes it for Act 2). Logs carry `question_chars` and a 12-hex `question_sha`, never the question text.

## 4. Failure & rollback

Fails by: 503 + `Retry-After` when generations in flight hit `MAX_INFLIGHT`; `/readyz` 503 naming the failed check; 502 with the error kind on a backend failure (unchanged).
Revert: `git revert <sha>` per item (each item is its own commit).
Down migration: `ALTER TABLE chunks DROP COLUMN embed_model;` (data is derivable: re-ingest restores it).

```
Action:       apply db/init/002_embed_model.sql to the dev DB (ADD COLUMN IF NOT EXISTS, backfill 'BAAI/bge-base-en-v1.5', SET NOT NULL)
Impact:       every row of chunks gains a column; nothing is deleted
Recovery:     FULLY RECOVERABLE — DROP COLUMN, or rebuild the DB from corpus/*.md with rag.ingest (~2 min)
Alternatives: none needed; the backfill value is proven first by re-embedding sample chunks with bge-base and matching the stored vectors
```
```
Action:       tests/conftest.py applies every db/init/*.sql to a per-worker plantcare_test* DB each session (TRUNCATE per test, as today)
Impact:       only databases whose name ends in _test (asserted before any statement)
Recovery:     disposable by design
```

## 5. Proof plan

```
P1 llm.py: every failure is an LLMError      → verify: tests fake each path (claude missing, non-JSON stdout, is_error with empty result,
                                                 APIConnectionError, text-less response); each yields its kind; no other exception escapes
P2 api.py: pool, limit, health, logs, key     → verify: /ask still 200 after pg_terminate_backend on the pool's connections; MAX_INFLIGHT+1
                                                 concurrent requests → one 503 with Retry-After; /healthz 200; /readyz 503 on an empty chunks
                                                 table; one JSON log line per request with the request id and no question text; 401 without the key
P3 embed_model + atomic ingest                → verify: a failure mid-ingest leaves chunks unchanged; runner and /readyz refuse on a model mismatch;
                                                 stored dev vectors match a fresh bge-base embedding (cosine > 0.999) before the backfill runs
P4 eval gate + CI                             → verify: gate exits 1 when a candidate raises hallucination or drops recall; exits 0 on v1.1 → v2
                                                 if v2 holds; CI job runs the suite against a pgvector service (runs on GitHub once pushed)
P5 packaging                                  → verify: image builds; container /healthz and /readyz 200 against the compose db
P6 no-regression                              → verify: v2 config re-run on hardened code (v2.1): recall identical (retrieval is deterministic),
                                                 hallucination 0, errors 0
```

## 6. Model & budget plan

| step | tier | est tokens | why this tier (silent-failure risk) |
|---|---|---|---|
| P1 llm.py errors | sonnet (service-implementer) | 120K | every path is faked in a test; a wrong mapping fails loudly |
| P2 serving layer | opus (service-implementer) | 200K | COMPLEX: auth on a public endpoint and a concurrency limiter pass happy-path tests while being wrong |
| P3 migration + atomic ingest | opus (data-implementer) | 150K | COMPLEX: migration on live data; a wrong backfill mislabels every vector silently |
| P4 gate + CI | sonnet (service-implementer) | 100K | gate logic is table-tested; CI YAML fails loudly |
| P5 packaging, P6 no-regression, wiring | inline | 60K | integration across the workers' seams |
| review | opus (reviewer) | 150K | COMPLEX: security pass on auth and the migration |

## Open (named, not built this round)

Least-privilege DB role for the API (read-only on `chunks`/`documents`); per-client rate limiting (belongs at the gateway); answer cache; red-team prompt-injection eval set; streaming responses (needs the chat UI).
