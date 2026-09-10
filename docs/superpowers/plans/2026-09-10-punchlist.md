# Punchlist — plant-care-rag, Phases 0–2

Plan of record: `~/.claude/plans/ok-lets-plan-this-glistening-heron.md` (approved 2026-09-10).
A box is checked only when DONE and verified with pasted output. Ledger rows: `| step | tier | est | actual |`.

## 0.1 WSL2 + Docker Desktop (Keegan)
- [ ] `wsl --install` (admin) → reboot → Docker Desktop installed, WSL2 backend
- [ ] verify: `docker run --rm hello-world` prints the hello message

## 0.2 Repo scaffold
- [x] dirs, `uv init --python 3.12`, pyproject with CPU torch index, .gitignore/.gitattributes/.env.example, LICENSE
- [x] deps installed; verified: `torch 2.14.0+cpu cuda False`, `sentence-transformers 6.0.1`
- [ ] first commit
- ledger: `| 0.2 | inline | 15K | — |`

## 0.3 Docker compose + schema
- [x] `docker-compose.yml` (pgvector 0.8.6-pg17, named volume, healthcheck, init mount, port bound to 127.0.0.1)
- [x] `db/init/001_schema.sql` (documents, chunks, HNSW cosine, GIN tsv, hybrid_search RRF)
- [ ] verify (needs 0.1): `docker compose ps` healthy; `\dx` lists vector; `SELECT * FROM hybrid_search('anthurium yellow leaves', array_fill(0,ARRAY[768])::vector, 5)` runs
- ledger: `| 0.3 | inline | 10K | — |`

## 0.4 Contract
- [x] `docs/design/contract-pipeline.md` written
- [ ] Keegan approval message
- ledger: `| 0.4 | inline (COMPLEX) | 12K | — |`

## 0.5 Corpus session 1 — general deflasking/acclimation protocol
- [ ] interview answered by Keegan
- [ ] `corpus/general-acclimation.md` structured, `[CONFIRM]` markers resolved, `verified: true`
- ledger: `| 0.5 | inline with Keegan | 20K | — |`

## 1.1 Corpus sessions 2–6 (monstera, alocasia, philodendron, anthurium, water/pests)
- [ ] one doc per session minimum, verified by Keegan
## 1.2 `rag/ingest.py` + `rag/embed.py` + `rag/db.py`
- [ ] TDD: chunker cap/split/slug-stability tests fail → pass
- [ ] verify: `uv run python -m rag.ingest` chunk count matches; rerun inserts 0
## 2.1 `rag/retrieve.py`
- [ ] verify: 10 hand-checked queries hit expected chunk in top-5; genus filter test
