# Punchlist — plant-care-rag, Phases 0–2

Plan of record: `~/.claude/plans/ok-lets-plan-this-glistening-heron.md` (approved 2026-09-10).
A box is checked only when DONE and verified with pasted output. Ledger rows: `| step | tier | est | actual |`.

## 0.1 WSL2 + Docker Desktop (Keegan)
- [x] `wsl --install` (admin) → reboot → Docker Desktop installed, WSL2 backend (Keegan, 2026-09-10)
- [x] verify: Keegan confirmed docker works in terminal; architect: `Docker version 29.7.2`, `Compose v5.5.1`

## 0.2 Repo scaffold
- [x] dirs, `uv init --python 3.12`, pyproject with CPU torch index, .gitignore/.gitattributes/.env.example, LICENSE
- [x] deps installed; verified: `torch 2.14.0+cpu cuda False`, `sentence-transformers 6.0.1`
- [x] first commit `2253611`
- ledger: `| 0.2 | inline | 15K | — |`

## 0.3 Docker compose + schema
- [x] `docker-compose.yml` (pgvector 0.8.6-pg17, named volume, healthcheck, init mount, port bound to 127.0.0.1)
- [x] `db/init/001_schema.sql` (documents, chunks, HNSW cosine, GIN tsv, hybrid_search RRF)
- [x] verified: `plant-care-rag-db-1 Up (healthy) 127.0.0.1:5432`; `vector 0.8.6`; tables chunks+documents; indexes chunks_hnsw (hnsw cosine), chunks_tsv (gin), chunks_genus; `hybrid_search(...)` → 0 rows, no error
- ledger: `| 0.3 | inline | 10K | ~12K |`

## 0.4 Contract
- [x] `docs/design/contract-pipeline.md` written
- [x] Keegan approved 2026-09-10: "Contract pipeline approved"
- ledger: `| 0.4 | inline (COMPLEX) | 12K | — |`

## 0.5 Corpus session 1 — general deflasking/acclimation protocol
- [x] interview answered by Keegan
- [x] `corpus/general-acclimation.md` + `general-substrate-water.md` structured, markers resolved, verified
- ledger: `| 0.5 | inline with Keegan | 20K | — |`

## 1.1 Corpus sessions 2–6 (monstera, alocasia, philodendron, anthurium, water/pests)
- [x] sessions 2-6 done same day: 18 docs / 65 chunks, all `verified: true`, 0 CONFIRM markers; Keegan: "All are verified so far besides for the little additions"
## 1.2 `rag/ingest.py` + `rag/embed.py` + `rag/db.py`
- [x] TDD: RED (ModuleNotFoundError) → GREEN `13 passed` — chunker (7), embed prefixes (3), ingest integration on Docker DB (3: upsert+skip unverified, idempotent re-ingest, --prune)
- [x] verified: `ingested 18 docs, 65 chunks, pruned 0, skipped 0` twice (idempotent); max chunk 617 chars, 0 splits
- [x] bug caught by real corpus: YAML rejected unquoted titles with colons → RED tests → flat key/value frontmatter parser, pyyaml removed, `19 passed`
## 2.1 `rag/retrieve.py`
- [x] TDD: RED (ImportError) → GREEN `17 passed` — vector ranking, genus filter (excludes others, keeps general), hybrid keyword surfacing, bad mode rejected
- [x] verified: `eval/sanity.py` → top-5 hits vector 9/10, hybrid 9/10; miss = "variegated monstera going all green" at rank 6 (logged in eval/notes.md for Phase 5)
- ledger: `| 2.1 | inline | 25K | ~15K |`
- ledger: `| 1.2 | inline | 40K | ~30K |`

## 3.1 `rag/generate.py` + `prompts/answer.md` v0 + schema
- [x] TDD: RED (ModuleNotFoundError) → GREEN `25 passed` — cited answer + usage, question wrapped as data, citation outside retrieved set → `citation_invalid`, refusal exact string, refusal drops citations, 500-char cap
- [x] verified live via `claude -p` (cc): seeded → `refused False`, citations `[general-acclimation#humidity-...]`; off-topic → refused; empty context → refused; 22 s / 3 calls
- note: v0 prompt asks for inline `[chunk_id]` brackets but the model returned a clean answer + correct `citations` array — acceptable for v0, revisit in prompt v1 if the eval wants inline marks
- ledger: `| 3.1 | inline (COMPLEX) | 30K | ~25K |`

## 3.2 `rag/api.py` (FastAPI, model loaded once)
- [x] TDD: RED (ModuleNotFoundError) → GREEN `30 passed` — response keys, 4 timings, k clamp 99→20, genus hoya→None, 501 chars→422, bad mode→422, refusal passthrough
- [x] DEFECT caught by live curl: prune test against the dev DB wiped all 65 chunks → `tests/conftest.py` creates isolated `plantcare_test` from the init SQL; suite re-run leaves dev at 65 (CODE-LEARNINGS 2026-09-10 test-isolation)
- [x] verified live: `embedding model BAAI/bge-base-en-v1.5 loaded in 10.6s` once; alocasia leaf-drop (hybrid) → 2 citations, embed 25 ms / retrieve 7 ms / generate 11.9 s (CLI-bound); monstera flowering → refused; 501 chars → 422
- ledger: `| 3.2 | inline (single seam < 150 lines; contract estimated dispatch, delegation floor says inline) | 20K | ~35K incl. isolation fix |`
