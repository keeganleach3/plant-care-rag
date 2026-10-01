# Direction contract — chat UI (B · Conservatory)

Locked 2026-09-30. Keegan: "Go with B". The comp is the direction: boards `B-welcome` and `B-answer` on
https://claude.ai/artifact/GyQq2EQys9m5yMyFjZ6Nh6. This file records what the comp leaves open, and each place the build
departs from it, with the reason. API side: [chat-ui-api.md](../contracts/chat-ui-api.md).

## 1. Read

Product chat UI · Operate · Keegan demoing it locally, and README readers who see its screenshots · the one thing the
viewer leaves with: every answer comes from named sections of one grower's notes, and it says so plainly when the notes
don't cover the question.

Dials (1–10): Variance 3 · Motion 2 · Density 4. It is a calm tool. Motion is limited to state changes (loading pulse,
drawer slide, all off under reduced motion). The answer and its sources sit side by side.

## 2. Story

| Act | Beat it carries |
|---|---|
| 1. Welcome | What the answers come from, and four questions it can answer |
| 2. Answer | The answer in the one forest block; what was searched; how long it took; the sources beside it, cited or not used, each opening to the full section |
| 3. Refusal | "I don't have information on that in my notes", with the closest sections it searched |
| 4. Library, history | Everything it knows (notes → sections → text); past questions reopen instantly, with no new call |

## 3. Devices

| Act | Device | Why here |
|---|---|---|
| all | 09 Operable module | The page is a tool, not a read |
| 2 | House product style: depth, not lines; one bold colour block | White cards on a sage canvas; the forest gradient is kept for the AI's own voice, so the eye lands on the answer first |
| 2 | AI provenance baked in (product.md) | "From the grower's notes", "Cited 3 of 5 retrieved sections", "Answered in 14.9 s · retrieval 98 ms" |
| 1 | 02 Extreme cropping, decoration only | The monstera line drawing leaves the frame on the right, clipped inside the page (no scroll extent) |

## 4. Palette

The comp's own tokens (not from the colour library). All text pairs pass AA; ratios measured 2026-09-30.

| Hex | Assigned meaning |
|---|---|
| `#ECF0EB` canvas · `#FFFFFF` card | Depth: cards sit on the canvas, no borders |
| `#16241C` ink | Text 14.0:1 on canvas; the Ask pill (dark ink primary, 14.9:1) |
| `#4F6356` secondary · `#6B7F72` greeting line 1 | Secondary text 5.6:1; the greeting's first line is 46px (3.7:1, large text) |
| `#2F7A52` accent · `#1F5A3D` brand | Links, icon chips at 13% tint, the "Cited" badge (6.5:1), the logo tile |
| `#22603F → #174A31` answer · `#F2F7F3` / `#BFE3CB` on it | The one colour block per view: the answer only (text 6.9:1, meta 5.4:1) |
| `#E2E8E2` sunken · `#4A5E51` / `#2E4337` on it | "Not used" source tiles (5.6:1, 8.6:1) |

Registers: shadows carry hue `rgba(22,48,31,…)`, never black. Radii: card 20 · tile 14 · chip 10 · pill 999. Face:
Geist, weights 420 display / 560 titles. Light theme only.

## 5. Numbers on screen (no charts)

| Number | Source |
|---|---|
| "22 notes · 96 sections" | live `GET /sources` (counts of what is indexed, not a constant) |
| "Cited 3 of 5 retrieved sections" | live `/ask`: `citations` of `chunks` |
| "Answered in 14.9 s · retrieval 98 ms" | live `/ask` `timings`: `total_ms`, and `embed_ms + retrieve_ms` |
| "0/500" | the question length against `MAX_QUESTION` in `rag/generate.py` |

## 6. Build decisions the comp leaves open

- **Rail:** logo (starts a new chat), New chat, History, Library. Cut from the comp: *Search chats* (becomes the filter
  inside History), *Settings* (nothing to set: the served config is the one the eval froze), the *K avatar* (there is no
  sign-in, so "Signed in as" would be false).
- **"Ask a follow-up…" → "Ask another question…"** Each question is answered on its own; the API keeps no conversation,
  so "follow-up" would promise context it never uses.
- **Thread header:** the first question, truncated. No title-generation call.
- **Query chips** ("Searched 3 ways"): from `queries`; the first is labelled "the whole message". One query → no chips.
- **Sources:** the aside at ≥1280px; below that, inline under each answer. A card opens to the full section text. With
  several answers in a thread, the aside follows the active answer (ring on it); an answer's "Cited n of k" footer makes
  it active.
- **Refusal:** a white card, not the forest block, labelled "Not in the grower's notes" (the comp's "From the grower's
  notes" read as a contradiction above the refusal line), then "Closest sections searched", all marked not used.
- **Loading:** the question bubble, then an answer-shaped placeholder with elapsed seconds. No invented stages: the
  client cannot see them.
- **Errors, in plain words, each with Retry:** busy (503 busy), notes database unreachable (503 db, "is Docker
  running?"), index built with another embedding model (503 embed_model), service unreachable (proxy 503 unreachable,
  with the start command), generation failed (502 + kind: timeout, CLI error, invalid answer; the service retries a
  rate limit itself and reports one that persists as a CLI error). When the notes fail to load, the composer and the
  library give the same reason in the same words.
- **Genus:** native select: All genera, Monstera, Alocasia, Anthurium, Philodendron. A genus keeps the general notes in
  scope (that is how the search filter works), and the option says so.
- **History:** threads saved in this browser only (localStorage), reopened without a new call; clear all.
- **Scale:** the root size is 16px up to 1440 wide, then grows with the viewport to 20px at 2400 and holds; everything is
  in rem, so the composition grows with it, then centres while the canvas keeps bleeding. At 390 the rail becomes a top
  bar and the prompts stack.
- **One viewport, by construction:** the app is `h-dvh` with its own scroll regions, so the sweep's hero-fill check has
  nothing to measure (`headSelector: ""`).
- **Focus:** after asking or retrying, the caret returns to the question box on devices with a fine pointer (on touch
  it would raise the keyboard over the answer); one polite live region per thread announces "Waiting for the answer."
  and then the answer or the refusal; errors use `role="alert"`.
- **Dev fixtures:** in development only, `/?fixture=<name>` seeds a recorded state (answer, thread, refusal, loading,
  error, library) from dev-set eval rows, so every state can be swept and shot without the model. Production builds
  drop it. Never a holdout row.

## 7. Assets needed from Keegan

None.

References: https://dribbble.com/shots/25963464-Ai-chat-ui-design · Comp:
https://claude.ai/artifact/GyQq2EQys9m5yMyFjZ6Nh6 (`B-welcome`, `B-answer`)
