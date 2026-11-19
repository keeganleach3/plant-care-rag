# Punchlist — 2026-09-30 — finish line: scale over-build, chat UI, publishing

Keegan's answers (2026-09-30), one block each. A box is checked only when DONE with evidence.

## 1 — "ok on the sentence"
- [x] humidity sentence applied (`930e18c`), re-ingested, dev retrieval identical to v3 (23/23); Docker Desktop's stale-socket failure recovered first (both socket folders moved aside, one launch; engine 29.7.2)

## 2 — "What would be the recommended build for a production level rag, imagine way larger scale ... lets over build it to show what we're capable of and understand."
- [x] explainer and plan: `docs/design/scaling-architecture.md` (`12beed6`): what breaks at scale and what production does; six tracks (A multi-part questions, B documents/PDFs + queue, C millions of vectors + haystack + reranker crossover, D BM25 hybrid, E ACL/RLS + poisoned documents, F verification + tracing), each with its proof
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
- [x] Keegan (2026-09-30): the superseded status doc is deleted and three lines in the other docs were reworded (the `rag/llm.py` attribution line stays: it credits copied code)
- [ ] flip to public on his go

## 6 — "I can open it when we demo it but seems like we have more changes to do."
- [x] noted; Docker started for this round's ingest

## 7 — "Go with B" (chat UI build)
Contracts: `docs/design/contract-chat-ui.md` (direction and build decisions), `docs/contracts/chat-ui-api.md` (API side).
The UI lives in `web/` (a Next.js app inside `app/` would put its routes at `app/app/`).

### 7.1 API: `GET /sources` — service-implementer
Fence: `rag/api.py`, `tests/test_api.py`. Shape and errors: chat-ui-api.md §3–4.
- [x] test first: lists every indexed section grouped by note, notes by genus then title, sections in ingest order; section count equals `SELECT count(*) FROM chunks` (fails today: 404) — `test_sources_lists_every_indexed_section_by_note_genus_then_title_in_ingest_order` failed first with `assert (404 == 200)`, passes (`b3a847a`): exact body over 3 notes / 5 sections whose file order, genus-then-title order and heading order all disagree
- [x] test: with `API_KEY` set, no bearer → 401 — `test_sources_needs_the_bearer_key_when_api_key_is_set` failed first with `assert (404 == 401)`; now no header and a wrong bearer → 401 `WWW-Authenticate: Bearer`, key absent from the body; the right bearer → 200
- [x] test: database unreachable → 503 `db` with `Retry-After: 5` — the real-pool test (`127.0.0.1:1`) now covers it too, renamed `test_an_unreachable_database_fails_ask_readyz_and_sources_within_seconds`; failed first with `assert (404 == 503)`; now 503 `{"detail": "db"}`, `Retry-After: 5`, under 10 s
- [x] route in `rag/api.py` on the existing pool and `authorize` dependency; full suite green (paste the last line) — `b3a847a`: `175 passed, 1 warning in 23.24s` (173 before; the warning pre-dates it). Mutants 5/5 killed: no `authorize`, `OperationalError` unmapped, borrow without the 2 s timeout, title order dropped, sections by heading. Live on a scratch instance (:8731, random `API_KEY`, dev DB): no bearer → 401; bearer → 200, 22 notes, 96 sections = 96 `chunks` rows, same chunk_id set, genus-then-title order; database unreachable → 503 `{"detail":"db"}`, `retry-after: 5`, in 2.0 s
- [x] architect verified: live service on :8000 (`/readyz` → ready, 96 chunks), then through the web proxy: `GET localhost:3100/api/sources` → `200`, `x-request-id` set, 22 notes, 96 sections, genus-first order. Startup warning now names `/sources` too (`4 passed` on the warning and sources tests). Known limits, accepted: `embed_model` reports the configured model (equal to the stored one once the startup check passes); "ingest order" is `chunks.id`, so a section added to an existing note lists last until a fresh ingest

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
- [x] Rail: logo (new chat), New chat, History, Library, with labels for screen readers; a top bar below 768px — W1: icon buttons with `aria-label`s, History and Library with `aria-haspopup="dialog"` and `aria-expanded`; at 1440 the items sit at y 24/98/154/210 as in the comp; nav 767×64 at 767 wide, 88 wide at 768
- [x] Welcome: two-tone greeting, subtitle, four prompt cards with icon chips drawn from the pool, "Refresh prompts", the monstera drawing clipped inside the page — W1: same probe on the comp and the build at 1440×900: h1 334,145 / 334,144; cards 195×181 at y 349 / 347; composer 820×151 at y 604 / 605; drawing 620×760 at 940,60 in both. Refresh pages the pool four at a time; all pages share one grid cell, so nothing below moves (checked on all three). Drawing clipped by the page, anchored to the composition: hscroll 0 at 390/767/768/1024/1440/1920/2560/3440/5120
- [x] Composer, welcome variant: textarea, genus select (a genus keeps general notes, and says so), "Splits multi-part questions", note and section counts from `/sources` (offline state with "Try again" when it fails), `n/500`, the Ask pill. Docked variant: the pill input, "Ask another question…", the genus select as a small pill, the Ask pill. Enter submits, Shift+Enter is a new line; Ask disabled when empty, over 500, offline or pending — W1: with `/api/ask` stubbed, Enter sent `{"question":"line one\nline two","genus":"monstera"}` (Shift+Enter made the new line); `501/500` disabled, 500 after trimming enabled, blank disabled; `?fixture=offline`: "Can’t reach the notes. Try again", Ask and prompt cards disabled; the genera sit under the option group "One genus, plus the general notes"
- [x] HistoryDrawer: this browser's threads, newest first, a filter box, reopen without a call, clear all — W1: native `<dialog>` + `showModal()`; Esc, backdrop and Close each close it and focus returns to History; a text drag out of the sheet does not close it; reopening a thread closed the drawer with 0 `/api/ask` calls; Clear all asks "Clear 3 saved conversations?" first, and the pressed button becomes Cancel
- [x] LibraryDrawer: notes grouped by genus → sections → full text; counts; offline state — W1: "22 notes · 96 sections"; Alocasia 4 · Anthurium 3 · General 9 · Monstera 3 · Philodendron 3 (the `/sources` order); note → section → text as nested `<details>`; offline shows "Can’t reach the notes. Try again"
- [x] typecheck, build, sweep, route shots at 1920 and 390 (pasted) — W1: `tsc --noEmit` exit 0; build `✓ Generating static pages using 7 workers (6/6)`; sweep `verify-sweep: 22 failing, 0 warn, 0 ignored · 10 routes × 1 scheme(s) · h-scroll 390/1440/1920/2560/3440/5120` — mine: `focus … TEXTAREA "Your question"` on all 10 routes (the ring is on the composer card, see the W1 report); `NEXTJS-PORTAL` is the dev overlay; `void-mid` on loading/error/busy is 7.4's; `library`, `history` clean. Shots: `route-shots.mjs` for `/` at 2558 and 1920 (it cannot write `?fixture=` file names on Windows), a scratch Playwright capture at 390 and 1920 for `/`, library, history, offline, answer

### 7.4 Thread and sources — ui-implementer W2
Fence: `web/components/{Thread,Turn,AnswerCard,SourcesPanel,SourceCard}.tsx` and any new file under `web/components/turn/`.
Port styles from `B-answer.dc.html`; decisions in contract-chat-ui.md §6.
- [x] header (the first question, truncated), question bubble, query chips ("Searched n ways", first chip "the whole message"; none for one query) — W2: the header is an `h1` on one line with an ellipsis; `answer` shows "Searched 3 ways", "the whole message" and the two clauses; f11 and n03 (one query each) show none. Same probe on the comp and the build at 1440×900 (comp / build): bubble 360,72 596×79 / 360,74 596×79; chips 788×68 / 788×67; answer 168,255 788×405 / 168,256 788×411 (its footer button is 24 tall for the tap target); aside head 372×30 / 372×29; first cited card 372×153 / 372×150
- [x] AnswerCard: forest gradient, "From the grower's notes", paragraphs, footer "Cited n of k retrieved sections" (a button that makes the answer active) and "Answered in x s · retrieval y ms" — W2: m06 reads "Cited 3 of 5 retrieved sections" and "Answered in 14.9 s · retrieval 98 ms" (14865 ms; 83.4 + 14.3 ms). On `thread` at 1440, pressing f11's footer moved the aside to "1 cited · 4 not used" and the ring (2px accent outline, only with the aside and two or more turns) to f11. Keyboard focus on the forest block: `solid 2px rgb(242, 247, 243)`. Below 1280 the footer is text: the sources sit under each answer, so there is nothing to switch
- [x] refusal card; loading placeholder with elapsed seconds; error card per kind with Retry. Wording (`error.kind`, then `detail` for 502s):
  busy → "The service is answering other questions right now." (+ "Try again in n s" from `retryAfter`) ·
  db → "The notes database isn't reachable. Is Docker running?" ·
  embed_model → "The index was built with a different embedding model. Re-ingest the notes, then try again." ·
  unreachable → "Can't reach the answer service. Start it from the project folder with `uv run uvicorn rag.api:app`." (detail "web server" → "Can't reach this app's server.") ·
  timeout → "No answer after 150 seconds, so the app stopped waiting." ·
  generation + timeout → "The model took too long to answer." · + cli_error → "The model call failed." · + schema_invalid → "The model's reply came back malformed, so it was withheld." · + citation_invalid → "The answer cited a section it wasn't given, so it was withheld." · + model_mismatch → "A different model answered than the one configured, so the answer was withheld." · + refusal → "The model declined to answer." · + anything else → "Generation failed (detail)." ·
  rejected → "The service rejected this app's key. Check RAG_API_KEY in web/.env.local." · unknown → "Something went wrong (status)."
  Answer text: paragraphs split on blank lines; lines starting "- " or "1. " become lists; text nodes only. Never show raw scores.
  — W2: refusal is a white card (n03's line, "Cited 0 of 5 retrieved sections"). Loading: a white answer-shaped card, "Waiting for the answer" and a ticking count (5 s → 7 s); pulse `pulse 2s infinite`, `none` under reduced motion; with `/api/ask` stubbed, the polite region read "" at 100 and 400 ms and "Waiting for the answer." at 1200 ms, then stayed put. Errors: `error` → "The model took too long to answer."; `busy` → the busy line with "Try again in 5 s" counting down; Retry (dark-ink pill) re-sent and settled, and is disabled while another question is pending; a stubbed 502 `cli_error` read "The model call failed."; the only console line was the stubbed 503's own network error. The wording sits verbatim in `turn/Failed.tsx` (`<code>` for the uvicorn command); `parts()` in `AnswerCard.tsx` builds `p`/`ul`/`ol` from text nodes (checked: blank-line paragraphs, a lead-in line then `- ` items, `1. ` then `- `, CRLF, "-5 degrees" stays prose); no score is rendered
- [x] SourcesPanel: the aside at ≥1280px, inline below; cited cards and not-used tiles; each opens to the full section; follows the active answer — W2: cited cards in citation order, then not-used tiles in retrieval order; each is a `<details>` that opens to the full section text (the excerpt is 3 lines when closed); keyed by turn, so following another answer starts closed; a refusal's list is titled "Closest sections searched" with "5 not used"; inline under each answer at 1279 and 390, aside padding at `xl` only
- [x] typecheck, build, sweep, route shots at 1920 and 390 for `?fixture=answer|thread|refusal|loading|error` (pasted) — W2: `tsc --noEmit` exit 0; eslint on the fenced files exit 0; build `✓ Generating static pages using 7 workers (6/6)`; sweep `verify-sweep: 23 failing, 0 warn, 0 ignored · 10 routes × 1 scheme(s) · h-scroll 390/1440/1920/2560/3440/5120` — mine: `void-mid` on loading, error and busy at 1440 and 1920, and on refusal at 1920 (one short turn leaves canvas down to the composer; placeholder bars count as ink-free); the rest are 7.3's `TEXTAREA "Your question"` focus and the dev overlay's `NEXTJS-PORTAL`. Shots: `route-shots.mjs` cannot write `?fixture=` file names on Windows, so a scratch Playwright capture at 1920×1080, 390×844 and 2558×1270 for answer, thread, refusal, loading, error and busy; hscroll 0 on each, and at 768, 1279 and 1280

### 7.5 Verify and review — architect
- [ ] reviewer on the diff against both contracts and this punchlist
- [x] verify-sweep on every fixture route: `verify-sweep: 7 failing, 0 warn, 8 ignored · 10 routes × 1 scheme(s) · h-scroll 390/1440/1920/2560/3440/5120`; the 7 are the one-short-turn `void-mid` bands, now matched by reasoned entries (the first keys used the printed double space; replaying that run's findings through `partition`: `findings 7 ignored 7 still active 0`). The 8 `focus` findings: the ring is drawn on the composer card, probed (`FORM outline 2px solid rgb(47, 122, 82)` on keyboard focus). Horizontal scroll: none at any width
- [x] shots read at 2558×1270 (welcome, answer, library), 1920×1080 (thread, refusal), 1440×900 (answer), 390×844 (welcome, answer), plus 3440 and 1280 measured: `scrollWidth/clientWidth` equal on all 25. Seen and fixed: at 2558 the 404px aside sat ~490px from the answer and truncated note titles → `w-[max(25.25rem,30%)]`; a refusal card said "From the grower's notes" above "I don't have information on that in my notes" → "Not in the grower's notes"
- [x] impeccable audit: detector `[]` on `web/components` and `web/app`; read-through fixed `aria-pressed` on the "Cited n of k" switch in multi-answer threads and one duplicated helper. Scores: accessibility 3, performance 4, responsive 4, theming 3 (light only, by contract), integrity 4 = 18/20
- [x] live on `cc` through the UI: the soil-mix prompt answered in 9.5 s (2 of 5 cited, titles from live `/sources`); "whats a good chicken marinade" refused in 6.9 s (0 of 5, closest sections listed); Alocasia scope retrieved only `general-*` and `alocasia-*` sections (log line `4050d26b…`); History saved the 3-question thread, Esc closed it, focus returned to History. Proof 4: a production build with a random marker as `RAG_API_KEY` has the marker in no shipped file (only Turbopack's local build cache, never served); the one `RAG_API_KEY` string in client code is the "rejected" error message naming the setting; no fixture text in client chunks. Proof 7: request id `e654e098…` from the proxy appears in the service's log line, question logged as length and hash only. Follow-up found: the genus scope filters retrieval but the model is not told it, so a scoped question can lead with general timing (a prompt change, needs an eval run)
- [x] CI web job (lint, typecheck, build) green on GitHub: run 36799717715 on `d09f1ff`, `web: success` (`✓ Compiled successfully in 5.9s`), `test: success` (`175 passed, 1 warning in 29.92s`)

### 7.7 Review fixes — reviewer (opus, read-only): no blockers, 5 major, 22 minor
- [x] SEC-1 (major) the UI listened on 0.0.0.0, so another device could use its key → `-H 127.0.0.1` on `next dev` and `next start`; `Get-NetTCPConnection`: `127.0.0.1 3100`, `127.0.0.1 8000`
- [x] SEC-2 (major) no Host, Origin or content-type check: a cross-site no-cors POST or a rebound DNS name reached the keyed `/ask` → `refuse()` in `lib/upstream.ts`; live: Host attacker.example 403, Origin evil.example 403, Sec-Fetch-Site cross-site 403, Origin null 403, text/plain POST 415, same-origin GET 200
- [x] ERR-1 (major) a `/sources` failure at load always read "Can't reach the notes" → its `AskError` is kept and the composer and library use the §7.4 wording (`lib/errors.tsx`, shared with the error card); the offline fixture shows the start command
- [x] A11Y-1 (major) the answer's arrival was never announced → one polite region per thread; live: "Waiting for the answer." then "Answer ready. Cited 1 of 5 retrieved sections."
- [x] A11Y-2 (major) focus fell to `<body>` after the first question and after Retry → the caret returns to the question box on fine-pointer devices; live: `activeElement` TEXTAREA "Ask another question…"
- [x] minor, fixed: TIME-1 (the comment and the 504 message now say a retry can outlast 150 s and the service may still finish; one deadline across the service's retries is a service follow-up), KEY-1 (the key is checked at load and the error never quotes it), KEY-2 (`server-only`), COMPAT-1 (`Map.groupBy` → `reduce`; `app/error.tsx` with Next 16's `retry`), A11Y-3 (`:has()` fallback ring), A11Y-4 (one answer: a plain span, not a dead button), HIST-1 (saved only when an answer lands, so reopening doesn't reorder), HIST-3 (malformed stored threads dropped), HIST-4 (full storage drops the oldest thread), LIST-1 (a list continues across a blank line; `<ol start>`; 8/8 parser cases), CITE-1 (citations counted once), NUM-1 (`ASK_TIMEOUT_S`), DEV-1 (an unknown fixture loads normally), NIT-1 (`plural`), TEST-1 (the warning test asserts `/sources`), PROOF-1 (504 `{"detail":"timeout"}` in 10.3 s against a stub that never answers), REV-1 / CONTRACT-1 / CONTRACT-2 / CHECK-1 (contracts amended)
- [x] found while fixing: the offline line was a flex row, so the reason split into gapped pieces ("rag.api:app ." ) → one inline sentence; `code` gets a named mono stack
- accepted, not fixed: HIST-2 (after Clear all, the open conversation is saved again on its next answer: it is still on screen), HIST-5 (History doesn't refresh while open; reopening shows the new answer)
- [x] after the fixes: `tsc` and `eslint` clean; `175 passed, 1 warning in 44.38s`; production build `✓ Compiled successfully`

### 7.6 README preview — after 7.5
- [x] README: CI and license badges, the hero (`docs/images/chat-answer.png`, the m06 v3 answer replayed, 1440×900 at 2x), an at-a-glance line with every figure from `eval/results/v3/report.md` (recall@5 0.95 over 14, 0/9 hallucination, 0/14 false refusal, 13 c 1 p, P50 7773 ms total / 7747 ms generate); the UI in "How it works", the key row in the hardening table, UI steps in "Run it"
- [x] `docs/images/social-preview.png`, 1280×640, 207 KB: for Keegan to upload in the repo's Settings → Social preview (GitHub has no API for it)

## 8 — "i can also do research on some of the things ive learned about rag ... we plan more instead of just guessing"
- [x] sourced survey of production RAG practice: 44 pages opened, every number linked (`docs/design/rag-research-survey.md`); the 12 headline numbers re-opened by a second agent (7 confirmed, 5 corrected for scope or wording, 0 not found); two wrong recall intervals (the survey assumed n=38 and n=15) replaced by bootstrap intervals from the v3 report (0.857–1.000 over 14; 0.708–1.000 over 6). Brief for the planning session: `docs/design/rag-research.md`
- [ ] Keegan's findings + the survey → planning session → scope for the over-build (replaces the open decision in 2)

Final sweep after the review fixes: `verify-sweep: 0 failing, 0 warn, 15 ignored · 10 routes × 1 scheme(s) · h-scroll 390/1440/1920/2560/3440/5120` (the 15: the composer-card focus ring ×8 and one-short-turn bands ×7, each with its reason in `web/verify-sweep.ignore.json`).

## Open at round end
- Scope decision (2), after Keegan's research and the brief in 8
- Keegan: upload `docs/images/social-preview.png` (Settings → Social preview); the public flip (5) on his go
- Follow-ups found this round: the genus scope is not passed to the model (a prompt change, so an eval run); one deadline across the service's generation retries
