# Research brief: what the over-build should prove

2026-09-30. Input to the planning session, next to Keegan's own research. A survey agent opened 44 pages (papers,
official docs, engineering posts) and linked every number to the page it came from; a second agent re-opened the
sources behind the 12 headline numbers (7 confirmed, 5 corrected for scope or wording, none wrong in size). The full
survey, with every table and the re-check, is [rag-research-survey.md](rag-research-survey.md). The six tracks it
weighs are in [scaling-architecture.md](scaling-architecture.md).

## Where this project stands

| Fact | Number | Source |
|---|---|---|
| v3 recall@5, dev | 0.946 over 14 answerable questions; bootstrap 95% CI 0.857–1.000 | `eval/results/v3/report.md`, interval computed from its per-question rows |
| v3 multi-hop recall@5, dev | 0.875 over 6 questions; bootstrap 95% CI 0.708–1.000 | same |
| Corpus size | 96 sections, 6,223 words, about 8,900 tokens (characters ÷ 4, an estimate) | the indexed sections, 2026-09-30 |

Two consequences. With an interval that wide, no retrieval technique can show a real gain on this question set: the
next results have to come from a harder test. And the whole corpus fits in one prompt many times over. Anthropic's
guidance is that a knowledge base under about 200,000 tokens can go whole into the prompt
([Contextual Retrieval, 2024-09-19](https://www.anthropic.com/news/contextual-retrieval)). So any claim that retrieval
earns its place needs a whole-corpus-in-the-prompt comparison, and the scale work is where retrieval becomes necessary.

## What the evidence says

| Finding | Number | Source |
|---|---|---|
| Retrieval upgrades show their gains on large, varied corpora | Contextual retrieval cut top-20 retrieval failures 35% (embeddings), 49% (+ BM25), 67% (+ reranker), on codebases, fiction and papers | [Anthropic, 2024-09-19](https://www.anthropic.com/news/contextual-retrieval) |
| Rerankers can make things worse | Reranking deeper candidate lists fell below no reranking in 53.3% (academic) and 44.4% (enterprise) of settings | [arXiv 2411.11767](https://arxiv.org/html/2411.11767) |
| The kind of distractor decides the result | One closely related distractor cut accuracy by up to 25%; random filler raised it by up to 35% | [The Power of Noise, arXiv 2401.14887](https://arxiv.org/html/2401.14887) |
| Question decomposition helps modestly | Hits@10 0.781 → 0.810 alone, 0.872 with a reranker (MultiHop-RAG) | [arXiv 2507.00355](https://arxiv.org/html/2507.00355v1) |
| Graph-based RAG does not pay for fact lookup | The best graph method came within 1.6 points of RAG with a reranker; GraphRAG and RAPTOR were 11–26 points below; GraphRAG's global mode used 377× the tokens | [GraphRAG-Bench, arXiv 2506.05690](https://arxiv.org/html/2506.05690v3) |
| An LLM judge is not a domain expert | GPT-4 agreed with domain experts 60–68% of the time; experts agreed with each other 72–75% | [arXiv 2410.20266](https://arxiv.org/html/2410.20266v1) |
| Planted documents work | 5 injected texts per target question reached 90–99% attack success in databases of millions | [PoisonedRAG, arXiv 2402.07867](https://arxiv.org/html/2402.07867) |
| Published injection defences fail against adaptive attacks | All 12 defences tested were bypassed, most above 90% attack success | [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1) |
| Models abstain far less once given context | Claude 3.5 Sonnet 84.1% → 52%; a sufficient-context check raised correct answers 2–10% | [Sufficient Context, arXiv 2411.06037](https://arxiv.org/html/2411.06037) |
| PDF parsing is slow and unsettled | Docling 0.6–1.3 pages/s on CPU; OCR over 30 s per page; no opened benchmark compares the main parsers | [Docling, arXiv 2408.09869](https://arxiv.org/html/2408.09869) |
| Postgres full-text ranking has no global statistics | ts_rank and ts_rank_cd "do not use any global information" (so no IDF, by inference): the likely cause of this project's weak full-text leg | [PostgreSQL docs 12.3.3](https://www.postgresql.org/docs/current/textsearch-controls.html) |
| Smaller-unit indexing helps weak retrievers most | Propositions: +9 to +12 Recall@5 for unsupervised retrievers, +2.6 to +2.8 for trained ones (computed from the paper's table) | [Dense X Retrieval, arXiv 2312.06648](https://arxiv.org/html/2312.06648) |

This project already lived two of these: a cross-encoder reranker dropped recall@5 from 0.95 to 0.71–0.82, and the
Postgres full-text leg scored 0.78–0.82 against 0.95 for vector search alone (`eval/notes.md`).

## What it means for the plan

The evidence favours building a harder test and safer design over adding retrieval tricks. Proposed order, for the
planning session to confirm or change:

1. **Measure honestly (Track F, cheap):** a paired comparison with a bootstrap interval on every A/B; any automatic
   judge calibrated against Keegan's blind grades, with the agreement reported; and the whole-corpus-in-the-prompt
   comparison.
2. **Scale as a measurement study (Track C):** a haystack of closely related text, not random filler; approximate
   against exact search from 100k to millions of vectors; what quantization keeps; the depth at which a reranker starts
   to pay.
3. **Planted documents (Track E):** PoisonedRAG-style texts inside the haystack, attack success measured; containment
   by design (answers only from cited sections, a fixed refusal line, least privilege), not a filter.
4. **Model-based question splitting with a coverage check (Track A):** aimed at m04; expect a modest gain.
5. **PDF pipeline (Track B):** a parser comparison on real PDFs, only if PDFs matter to the story.
6. **BM25 (Track D):** last.

Evidence against, for this corpus: GraphRAG, LightRAG and RAPTOR; semantic and late chunking; proposition indexing;
page-image retrieval (ColPali); DiskANN (only vendor numbers found).

## Not verified

No page was opened for: ARES, independent pgvector scale benchmarks (ANN-Benchmarks), the main PDF parsers other than
Docling, parent-child chunking docs, OWASP's LLM guidance, OpenTelemetry's GenAI conventions, "Lost in the Middle".
Nothing here states their numbers.
