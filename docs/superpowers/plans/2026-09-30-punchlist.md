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

## Open at round end
Scope decision (2), UI pick (3), STATUS doc decision and the public flip (5).
