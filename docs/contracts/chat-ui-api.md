# Contract — chat UI API: `GET /sources` and the web proxy

Written 2026-09-30 under the standing go-ahead for engineering work (Keegan, 2026-09-24). The UI direction is
[contract-chat-ui.md](../design/contract-chat-ui.md). `/ask`, retrieval, generation and the eval are unchanged.

## 1. Blast radius

Data touched: read-only `SELECT` on `documents` and `chunks` (new `GET /sources`). No writes, no schema change.
Users affected: whoever runs the UI locally (Keegan's demo).
Worst case if wrong: the web proxy leaks the service's bearer key to the browser, and anyone with the page can call
`/ask` directly and spend the backend's budget (Max plan quota on `cc`, money on `api`).
Does not hit: `/ask`'s contract, the served config (vector, k=5, decompose on), eval results, the corpus.
Areas touched: `rag/api.py` (new route), `tests/test_api.py`, `web/` (new), `.github/workflows/ci.yml` (web job).

## 2. Trust boundaries

| Input enters at | Validated by (at that boundary) |
|---|---|
| Browser → `web/app/api/ask` body | ≤ 4096 bytes or 413 before any upstream call; passed through as JSON; the service validates fields (422) |
| Next server → RAG service | base URL only from server env `RAG_API_URL` (default `http://127.0.0.1:8000`), never from the request |
| Service response → browser | status and body passed through; the service's 5xx bodies are already kind-only (`api.py`) |
| `/sources` text and model answers → DOM | rendered as React text nodes; no `dangerouslySetInnerHTML` anywhere in `web/` |
| `?fixture=<name>` | read only when `NODE_ENV === "development"`; the production build drops the branch |

## 3. Data & secrets inventory

| Table | Access |
|---|---|
| `documents`, `chunks` | `SELECT` only, through the service's checked pool (statement timeout 10 s); single-tenant local DB, no RLS (see production-hardening.md) |

`GET /sources` → `200 {"embed_model": str, "notes": [{"slug", "title", "genus", "topic", "sections": [{"chunk_id",
"heading", "content"}]}]}`, notes ordered by genus then title, sections in ingest order. Same bearer check as `/ask`
when `API_KEY` is set; `503 db` (with `Retry-After: 5`) when the database is unreachable.

Secrets: `RAG_API_KEY` lives in `web/.env.local` (gitignored) and equals the service's `API_KEY`. The Next server
sends it as `Authorization: Bearer`. No `NEXT_PUBLIC_` prefix; it never reaches a client bundle or a response.

## 4. Failure & rollback

Fails by: service down → proxy `503 {"detail": "unreachable"}`; generation past 150 s → proxy `504 {"detail":
"timeout"}`; database down → `503 db` from the service, passed through.
Revert: `git revert <sha>`. The route is additive and `web/` is a new directory.
Down migration: n/a. Destructive steps: none.

## 5. Proof plan

```
1. GET /sources lists every indexed section, grouped by note → verify: new test fails today (404), passes after;
   section count equals SELECT count(*) FROM chunks
2. GET /sources needs the bearer when API_KEY is set → verify: test, 401 without it
3. GET /sources with the database unreachable → verify: test, 503 "db"
4. The key never reaches the browser → verify: grep the production build (web/.next) for the key value and for
   RAG_API_KEY: no match; the browser's request to /api/ask carries no Authorization header
5. Proxy caps the body → verify: curl a 5000-byte body: 413, and the service log shows no request
6. Service down → verify: curl /api/ask with the service stopped: 503 unreachable
7. End to end → verify: a real question through the UI on cc; answer and sources render; the proxy's X-Request-ID
   appears in the service's log line
```

## 6. Model & budget plan

| step | tier | est tokens | why this tier (silent-failure risk) |
|---|---|---|---|
| `GET /sources` + tests | service-implementer (opus) | 100k | touches the auth dependency: an open endpoint fails silently |
| proxy, page shell, types, fixtures | inline | — | security seam (the key) and the shared files both workers build on |
| welcome, composer, rail, drawers | ui-implementer (opus) | 200k | visual fidelity at five widths; no test covers it |
| thread, answer, sources, states | ui-implementer (opus) | 200k | same |
| review of the diff | reviewer (opus) | 100k | fresh eyes on the key handling and the states |
