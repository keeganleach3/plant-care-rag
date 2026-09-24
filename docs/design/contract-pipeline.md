# Contract — plant-care-rag pipeline (Phases 0–5)

Plan of record: `~/.claude/plans/ok-lets-plan-this-glistening-heron.md` (approved 2026-09-10).
Approval of this contract is one message from Keegan. Silence is not approval.

## 1. Blast radius

Data touched: two tables (`documents`, `chunks`) in a **local Docker Postgres** (`plantcare` db, port bound to `127.0.0.1` only) and files under `C:\Users\Keegan\Portfolio Projects\plant-care-rag`. No other project's database is read or written — no shared keys, no shared host. No other person's data or money is reachable by construction.

Worst cases that touch someone else:
- **Wrong care advice reaches a real grower.** The repo is public; someone runs it and follows an answer that kills a plant. Guard: the corpus carries only facts Keegan stated and marked `verified: true`; the model answers only from retrieved chunks with citations; the README states it is not advice.
- **Keegan's API key leaks** (`.env` committed). Guard: `.env` gitignored, `.env.example` holds no values, secret sweep in `verify` before every push, key rotated if it ever appears in history.
- **Eval numbers in the README are wrong** and a reviewer relies on them. Guard: every reported number is regenerated from `eval/results/<version>/results.jsonl` by `eval/run.py --report`; no hand-typed metrics.

## 2. Trust boundaries

| Untrusted input enters at | Validator at that boundary |
|---|---|
| Corpus markdown (`rag/ingest.py`) | Frontmatter required keys `title, genus, topic, verified`; `genus ∈ GENERA`, `topic ∈ TOPICS`; `verified != true` → skipped and logged; any `[CONFIRM]` marker → skipped; H2 body cap 2,000 chars after split |
| User question (`rag/api.py` → `rag/generate.py`) | Length cap 500 chars; wrapped in `<question>…</question>` with the system prompt stating it is data; `genus` param must be in `GENERA` or is dropped; `k` clamped to 1–20 |
| LLM output (`rag/generate.py`) | `--json-schema` / `output_config` schema `{answer, citations[], refused}`; local `validate()`; every `citations[i]` must be in the retrieved `chunk_id` set, otherwise the answer is rejected and logged (`citation_invalid`), never shown |
| `claude -p` stdout (`rag/llm.py`) | Trailing-JSON parse only; `is_error` → `errors.jsonl`; `modelUsage` must contain the requested model; tools, MCP, and settings disabled on every call |
| Anthropic SDK response (`api` backend, Act 2 only) | `stop_reason == refusal` → error row; `response.model == requested`; same schema validation |
| Eval questions (`eval/questions.jsonl`) | Required keys `id, question, category, gold_chunk_ids, must_refuse`; `gold_chunk_ids` is a list of any-of groups, one per required fact, and recall@k is the share of groups with at least one member retrieved (amended 2026-09-24, Keegan: "yes"); every gold chunk ID must exist in `chunks` or the run refuses to start; leakage check: a question's 10-word shingle found in any corpus file aborts the run |
| `.env` (`rag/config.py`) | Required keys checked at import; values never logged |

## 3. Data & secrets inventory

| Table | Where | Posture |
|---|---|---|
| `documents` | local Docker Postgres | no RLS (single local user `plant`); not network-reachable beyond loopback |
| `chunks` | local Docker Postgres | same; `embedding vector(768)`, `tsv` generated column |

| Secret / config | Lives in | Handling |
|---|---|---|
| `DATABASE_URL` | `.env` / `.env.example` | local credentials `plant:plant`, not secret, still not committed in `.env` |
| `LLM_BACKEND` | `.env` or shell | `cc` default; `api` only for the Act 2 grid, chosen per run |
| `ANTHROPIC_API_KEY` | `.env` (gitignored) | **Keegan pastes it** when Act 2 starts; Claude never reads it back or logs it |
| Claude Code OAuth (Max) | on the machine | used implicitly by `claude -p`; `--bare` not used (drops the login) |
| HF model cache | `~/.cache/huggingface` | ~420 MB bge-base download on first embed; no token needed |

## 4. Failure & rollback

- Ingest: a bad doc is skipped with a logged reason; the run continues. Chunk upsert keyed on `chunk_id`, so re-ingest after a corpus edit updates in place; a removed section is deleted by `--prune` only (explicit).
- LLM call: `errors.jsonl` row with class (`cli_error` / `timeout` / `model_mismatch` / `schema_invalid` / `refusal` / `citation_invalid`); never an empty answer scored as anything.
- Eval crash mid-run: `results.jsonl` row per `(question_id, rep)`; rerun resumes.
- Code rollback: `git revert <sha>`; each step is its own commit.

```
Action:       docker compose down -v   (drops the pgdata volume)
Impact:       documents + chunks + embeddings deleted
Recovery:     FULLY RECOVERABLE — corpus/*.md is the source of truth; `docker compose up -d` re-runs
              db/init/001_schema.sql and `uv run python -m rag.ingest` rebuilds everything (~2 min CPU embed)
Alternatives: `docker compose down` (no -v) keeps the volume
```

Chain: `down -v` is the only destructive operation in Phases 0–5. Nothing in this repo deletes corpus files.

## 5. Proof plan

| Step | → verify |
|---|---|
| 0.1 WSL2 + Docker (Keegan) | `docker run --rm hello-world` |
| 0.2 scaffold | ✅ `torch 2.14.0+cpu cuda False`, `sentence-transformers 6.0.1`, Python 3.12 via uv |
| 0.3 compose + schema | `docker compose ps` healthy; `\dx` shows `vector 0.8.x`; `hybrid_search` with a zero vector returns without error |
| 0.4 this contract | ✅ approved by Keegan 2026-09-10 |
| 0.5–1.1 corpus | each doc `verified: true`; `grep -c CONFIRM corpus/*.md` → 0 before ingest |
| 1.2 ingest | tests: cap, paragraph-boundary split, slug stability across two runs, unverified doc skipped; `SELECT count(*) FROM chunks` equals the chunker count; rerun → 0 inserts |
| 2.1 retrieve | 10 sanity queries logged with hit rank in `eval/notes.md`; genus filter test excludes other genera but includes `general` |
| 3.1 generate | `--sanity`: empty context → `refused: true`; seeded context → citations ⊆ retrieved; forged citation → `citation_invalid` |
| 3.2 api | startup log shows one model load; `curl` round-trip returns `timings` with four keys |
| 4.x eval | see plan; every results row has non-trivial `model`, `usage`, `grade`; report has no blank cells |

## 6. Model & budget plan (opening ledger entry)

Pipeline calls: `cc` backend on the Max plan, $0. Realistic answer call ≈ 3K in / 300 out; ~40 questions × ~6 versions × 1 rep ≈ 240 calls ≈ 0.8M tokens. Judge calls similar. Act 2 grid: 24 cells × 40 q × 3 reps ≈ 2,900 API calls ≈ 9M in / 1M out → Haiku ~$5, Sonnet ~$20 if the full grid runs on both; cap by running Sonnet on a 15-question subset (~$8 total).

Build agents (architect = Fable):

| step | tier | est tokens | actual |
|---|---|---|---|
| 0.2–0.4 scaffold, compose, schema, contract | inline | 40K | — |
| 0.5–1.1 corpus sessions | inline with Keegan | 6 × 20K | — |
| 1.2 ingest/embed/db + tests | inline (single seam, TDD) | 40K | — |
| 2.1 retrieve + tests | inline | 25K | — |
| 3.1 generate + prompt v0 | inline (COMPLEX: refusal behaviour is silent until eval) | 30K | — |
| 3.2 api | sonnet dispatch, fenced to `rag/api.py` | 20K | — |
| 3.3 chat UI (after design contract) | sonnet dispatch, fenced to `app/` | 80K | — |
| 4.2–4.4 grade/run/judge | inline (COMPLEX: a broken eval produces confident wrong numbers) | 60K | — |
| 5.x iterations | inline with Keegan | 5 × 15K | — |

Dispatch rule: honey worker directive, explicit `model`, file fence, punchlist ref. No agent runs `git stash`, `checkout`, `reset`, or `clean`.
