# Punchlist — 2026-09-30 — finish line: scale over-build, chat UI, publishing

Keegan's answers (2026-09-30), one block each. A box is checked only when DONE with evidence.

## 1 — "ok on the sentence"
- [x] humidity sentence applied (`cccf412`), re-ingested, dev retrieval identical to v3 (23/23); Docker Desktop's stale-socket failure recovered first (both socket folders moved aside, one launch; engine 29.7.2)

## 2 — "What would be the recommended build for a production level rag, imagine way larger scale ... lets over build it to show what we're capable of and understand."
- [x] explainer and plan: `docs/design/scaling-architecture.md` (`3717d57`): what breaks at scale and what production does; six tracks (A multi-part questions, B documents/PDFs + queue, C millions of vectors + haystack + reranker crossover, D BM25 hybrid, E ACL/RLS + poisoned documents, F verification + tracing), each with its proof
- [ ] Keegan's scope decision (tracks, public-text download for the haystack, GPU/CUDA) → then one contract + punchlist per track before code

## 3 — "AI design lets do something nice and clean, I like this interface: https://dribbble.com/shots/25963464-Ai-chat-ui-design but bring some plant theming into it."
- [x] reference read (both shots: dark and light welcome states; rail, two-tone greeting, four prompt cards, input with scope, counter, send)
- [x] three directions rendered on a canvas, welcome + answer state each, with real v3 output (m06 answer, its 5 retrieved sections, real timings): https://claude.ai/artifact/GyQq2EQys9m5yMyFjZ6Nh6
- [ ] Keegan picks or mixes → `docs/design/contract-chat-ui.md` locks it → build in `app/` → verify-sweep + route shots + impeccable audit

## 4 — "Unsure what you need from me here"
- [x] explained: nothing now; later, blind sheets for new answer versions and one blind grading of the 15 held-out answers at the end

## 5 — "Publish into github repo yes, we will need to build a nice summary preview in it as well"
- [x] history and tracked files scanned: no `.env`/credentials ever committed, no keys or tokens; only the local `plant:plant` fixture
- [x] private repo `keeganleach3/plant-care-rag` created and pushed; first CI run on GitHub: `173 passed, 1 warning in 24.42s` (run 36766986718)
- [ ] summary preview: README hero (UI screenshot/GIF), CI and license badges, at-a-glance results; social preview image 1280×640 (GitHub web setting)
- [x] Keegan (2026-09-30): "drop the framing issues". The superseded status doc is deleted; the other docs no longer name his other projects or call this a portfolio system (the `rag/llm.py` attribution line stays: it credits copied code). Git history still holds the old doc; purge only on his call, because a rewrite changes every hash since 2026-09-24 and the eval change notes cite commits by hash
- [ ] flip to public on his go

## 6 — "I can open it when we demo it but seems like we have more changes to do."
- [x] noted; Docker started for this round's ingest

## 7 — "Go with B" (chat UI build)
Contracts: `docs/design/contract-chat-ui.md` (direction and build decisions), `docs/contracts/chat-ui-api.md` (API side).
The UI lives in `web/` (a Next.js app inside `app/` would put its routes at `app/app/`).

### 7.1 API: `GET /sources` — service-implementer
Fence: `rag/api.py`, `tests/test_api.py`. Shape and errors: chat-ui-api.md §3–4.
- [x] test first: lists every indexed section grouped by note, notes by genus then title, sections in ingest order; section count equals `SELECT count(*) FROM chunks` (fails today: 404) — `test_sources_lists_every_indexed_section_by_note_genus_then_title_in_ingest_order` failed first with `assert (404 == 200)`, passes (`dd0dd90`): exact body over 3 notes / 5 sections whose file order, genus-then-title order and heading order all disagree
- [x] test: with `API_KEY` set, no bearer → 401 — `test_sources_needs_the_bearer_key_when_api_key_is_set` failed first with `assert (404 == 401)`; now no header and a wrong bearer → 401 `WWW-Authenticate: Bearer`, key absent from the body; the right bearer → 200
- [x] test: database unreachable → 503 `db` with `Retry-After: 5` — the real-pool test (`127.0.0.1:1`) now covers it too, renamed `test_an_unreachable_database_fails_ask_readyz_and_sources_within_seconds`; failed first with `assert (404 == 503)`; now 503 `{"detail": "db"}`, `Retry-After: 5`, under 10 s
- [x] route in `rag/api.py` on the existing pool and `authorize` dependency; full suite green (paste the last line) — `dd0dd90`: `175 passed, 1 warning in 23.24s` (173 before; the warning pre-dates it). Mutants 5/5 killed: no `authorize`, `OperationalError` unmapped, borrow without the 2 s timeout, title order dropped, sections by heading. Live on a scratch instance (:8731, random `API_KEY`, dev DB): no bearer → 401; bearer → 200, 22 notes, 96 sections = 96 `chunks` rows, same chunk_id set, genus-then-title order; database unreachable → 503 `{"detail":"db"}`, `retry-after: 5`, in 2.0 s
- [ ] architect verified: curl against the live service

### 7.2 Web shell — inline (architect)
- [x] scaffold `web/` (Next 16.3.8, TypeScript, Tailwind 4, Geist); tokens and the fluid root size in `globals.css`; `NEXT_DIST_DIR` so parallel dev servers don't collide (Next 16 locks its dist dir per `next dev`)
- [x] proxy routes `/api/ask`, `/api/sources` (`lib/upstream.ts`): key server-side only, 4096-byte cap read incrementally, `unreachable` 503 and `timeout` 504, `X-Request-ID`
- [x] `lib/types.ts`, `lib/api.ts` (fetch + error kinds), `lib/history.ts`, `components/Chat.tsx` (state and layout), component stubs with their props; `tsc` and `eslint` clean
- [x] fixtures from dev rows only (m06, f11, n03; m04's question for loading) plus a `/sources` snapshot (22 notes, 96 sections); `?fixture=` read only in development
- [x] launch entries (`rag-api`, `rag-web`, `rag-web-w1`, `rag-web-w2` in the session root's `.claude/launch.json`; `api`, `web` in the project's), `web/verify-sweep.config.json` (routes = every fixture, `readySelector: [data-ready]`), `.gitignore`
- [x] architect verified: `/?fixture=answer` renders the m06 answer on :3100; proof 5 `{"detail":"request body over 4096 bytes"} [413]` with and without Content-Length; proof 6 `503 {"detail":"unreachable"}` with an `x-request-id`, for both routes

### 7.3 Welcome and navigation — ui-implementer W1
Fence: `web/components/{Rail,Welcome,Composer,HistoryDrawer,LibraryDrawer}.tsx`, `web/lib/prompts.ts`.
Port styles from `B-welcome.dc.html`; decisions in contract-chat-ui.md §6.
Prompt pool (answerable; the first four are the comp's): How humid should the dome be for new TC plantlets? (drop) ·
What soil mix do tissue-culture Monstera go into first? (sprout) · Is one Barrina T5 at 8 inches enough for an albo?
(sun) · What's the best way to deal with thrips on baby aroids? (bug) · How much light do Alocasia plantlets need right
after potting? (sun) · How long before I start lowering the humidity on Alocasia? (drop) · Should tissue cultures get
fertilizer when they're first potted? (sprout) · My TCs arrived in a heat wave. Can the bags sit out for a few days?
(sun) · Is Thai Constellation care different from albo care? (sprout) · Leaves yellowed right after the dome came off.
Is it light or humidity? (drop) · Is an AC Infinity S16 at 10 inches for 14 hours enough for Philodendron? (sun) ·
Bugs showed up while my plants are still in the dome. Treat now or wait? (bug)
- [ ] Rail: logo (new chat), New chat, History, Library, with labels for screen readers; a top bar below 768px
- [ ] Welcome: two-tone greeting, subtitle, four prompt cards with icon chips drawn from the pool, "Refresh prompts", the monstera drawing clipped inside the page
- [ ] Composer, welcome variant: textarea, genus select (a genus keeps general notes, and says so), "Splits multi-part questions", note and section counts from `/sources` (offline state with "Try again" when it fails), `n/500`, the Ask pill. Docked variant: the pill input, "Ask another question…", the genus select as a small pill, the Ask pill. Enter submits, Shift+Enter is a new line; Ask disabled when empty, over 500, offline or pending
- [ ] HistoryDrawer: this browser's threads, newest first, a filter box, reopen without a call, clear all
- [ ] LibraryDrawer: notes grouped by genus → sections → full text; counts; offline state
- [ ] typecheck, build, sweep, route shots at 1920 and 390 (pasted)

### 7.4 Thread and sources — ui-implementer W2
Fence: `web/components/{Thread,Turn,AnswerCard,SourcesPanel,SourceCard}.tsx` and any new file under `web/components/turn/`.
Port styles from `B-answer.dc.html`; decisions in contract-chat-ui.md §6.
- [ ] header (the first question, truncated), question bubble, query chips ("Searched n ways", first chip "the whole message"; none for one query)
- [ ] AnswerCard: forest gradient, "From the grower's notes", paragraphs, footer "Cited n of k retrieved sections" (a button that makes the answer active) and "Answered in x s · retrieval y ms"
- [ ] refusal card; loading placeholder with elapsed seconds; error card per kind with Retry
- [ ] SourcesPanel: the aside at ≥1280px, inline below; cited cards and not-used tiles; each opens to the full section; follows the active answer
- [ ] typecheck, build, sweep, route shots at 1920 and 390 for `?fixture=answer|thread|refusal|loading|error` (pasted)

### 7.5 Verify and review — architect
- [ ] reviewer on the diff against both contracts and this punchlist
- [ ] verify-sweep on every fixture route (pasted)
- [ ] route shots read at 1440, 1920×1080, 2560 and 390
- [ ] impeccable audit
- [ ] live: real questions on `cc` (an answer, a refusal, a genus-scoped one); proofs 4 (key absent from the build) and 7 (request id in the service log)
- [ ] CI web job (lint, typecheck, build) green on GitHub

### 7.6 README preview — after 7.5
- [ ] hero screenshot at the top of the README; CI and license badges; an at-a-glance line
- [ ] social preview PNG, 1280×640, in `docs/images/` for Keegan to upload in the repo settings

## 8 — "i can also do research on some of the things ive learned about rag ... we plan more instead of just guessing"
- [ ] sourced survey of production RAG practice (research agent): every claim linked to a page the agent read → `docs/design/rag-research.md`
- [ ] Keegan's findings + the survey → planning session → scope for the over-build (replaces the open decision in 2)

## Open at round end
Scope decision (2, now after the research in 8), the public flip (5).
