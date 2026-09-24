# Retrieval notes

## Retrieval sanity — 2026-09-10 — BAAI/bge-base-en-v1.5

| query | expected | vector rank | hybrid rank |
|---|---|---|---|
| how humid should tc plants be when i first plant them | `general-acclimation#humidity-hold-100-percent-for-the-first-week` | 2 | 2 |
| my alocasia dropped all its leaves is it dead | `alocasia-acclimation#leaf-drop-during-alocasia-acclimation-is-normal` | 2 | 2 |
| thrips on my monstera what do i spray | `general-pests#thrips-rotate-sprays-every-four-days-or-use-systemic-granules` | 3 | 4 |
| black spots with rings on alocasia leaf | `alocasia-pests#leaf-spot-on-alocasia-what-it-looks-like` | 1 | 1 |
| my variegated monstera is going all green | `monstera-quirks#if-a-variegated-monstera-is-reverting-to-green` | 6 | 6 |
| what soil mix for tc anthurium | `general-substrate-water#first-substrate-mix-by-genus` | 2 | 2 |
| how long can i leave the tc bag unopened | `general-acclimation#unopened-bags-and-flasks-must-stay-below-75-f` | 1 | 1 |
| when should i repot | `general-acclimation#up-potting-wait-for-root-bound-do-not-disturb-the-roots` | 4 | 4 |
| caramel marble not growing | `philodendron-troubleshooting#slow-growth-on-philodendron-is-usually-normal` | 1 | 1 |
| how much light do variegated monsteras need | `general-light#established-plants-at-least-300-ppfd-for-12-to-14-hours` | 3 | 3 |

top-5 hits: vector 9/10, hybrid 9/10

## Retrieval sanity — 2026-09-24 — BAAI/bge-base-en-v1.5

| query | expected | vector rank | hybrid rank |
|---|---|---|---|
| how humid should tc plants be when i first plant them | `general-acclimation#humidity-hold-100-percent-for-the-first-week` | 2 | 2 |
| my alocasia dropped all its leaves is it dead | `alocasia-acclimation#leaf-drop-during-alocasia-acclimation-is-normal` | 2 | 2 |
| thrips on my monstera what do i spray | `general-pests#thrips-rotate-sprays-every-four-days-or-use-systemic-granules` | 3 | 4 |
| black spots with rings on alocasia leaf | `alocasia-pests#leaf-spot-on-alocasia-what-it-looks-like` | 1 | 1 |
| my variegated monstera is going all green | `monstera-quirks#if-a-variegated-monstera-is-reverting-to-green` | 7 | 7 |
| what soil mix for tc anthurium | `general-substrate-water#first-substrate-mix-by-genus` | 2 | 2 |
| how long can i leave the tc bag unopened | `general-acclimation#unopened-bags-and-flasks-must-stay-below-75-f` | 1 | 1 |
| when should i repot | `general-acclimation#up-potting-wait-for-root-bound-do-not-disturb-the-roots` | 4 | 4 |
| caramel marble not growing | `philodendron-troubleshooting#slow-growth-on-philodendron-is-usually-normal` | 1 | 1 |
| how much light do variegated monsteras need | `general-light#established-plants-at-least-250-ppfd-for-12-to-14-hours` | 3 | 3 |

top-5 hits: vector 9/10, hybrid 9/10


## Decomposition and reranking — 2026-09-24 — dev split, answerable questions (n=14), recall@5 over gold groups

v2 splits a message at "?" and where and/or/also/plus opens a new question, searches the whole message and each
clause, and fuses the rankings (RRF, c=60). Only m04 and m06 split on dev. Fusion choices on those two (probe, same
grade function the harness uses):

| fusion over whole + clauses | m04 | m06 |
|---|---|---|
| none (v1.1) | 0.00 | 0.50 |
| RRF c=60 (shipped as v2) | 0.50 | 1.00 |
| RRF c=10 | 0.50 | 1.00 |
| RRF over clauses only | 0.50 | 0.50 |
| round-robin | 0.50 | 1.00 |
| each clause's top hit reserved, rest by RRF | 1.00 | 0.50 |

m04's feeding clause ranks the first-watering section 1st on its own, but RRF favours the arrival and dome sections
all three rankings agree on. Left as a known miss; LLM decomposition (self-contained sub-questions, "them" resolved to
the plantlets) is the Act 2 candidate, at the cost of one extra model call.

Cross-encoder reranking of the fused top-20 (probe, not shipped). Scored against the whole message, or the best
score over the message and its clauses:

| reranker | passage text | recall@5 whole | recall@5 max over clauses | rerank ms median (CPU) |
|---|---|---|---|---|
| none (v2) | — | 0.946 | 0.946 | 0 |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | body | 0.708 | 0.744 | 136 |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | heading + body | 0.732 | 0.768 | 142 |
| BAAI/bge-reranker-base | body | 0.708 | 0.744 | 967 |
| BAAI/bge-reranker-base | heading + body | 0.815 | 0.815 | 1006 |

Every reranker fixes m04 and breaks others (f01, f04, f09, m02, m06, m10 across the four runs): on short
customer-voice questions over a 96-section corpus it promotes lexically close sections over the ones that answer.
Not shipped; revisit only if the corpus grows enough that first-stage recall drops.
