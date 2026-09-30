# Scaling plant-care-rag: from 96 sections to millions of documents

Keegan, 2026-09-30: "What would be the recommended build for a production level rag, imagine way larger scale. Multi
part questions and millions of files and PDFs exist in production environments. How would they handle that, lets over
build it to show what we're capable of and understand."

Part 1 explains how production systems handle scale and why. Part 2 is the plan to build a working, measured version
of each piece in this repo, locally and without paid APIs. Nothing in Part 2 starts until Keegan approves its scope.

---

## Part 1 — What changes at scale, and how production systems handle it

Today the system reads 22 markdown files (96 sections) and answers one message at a time. At millions of files, four
things break, in this order.

### 1. Ingestion stops being a script and becomes a pipeline

| Problem at scale | What production does | Why |
|---|---|---|
| Files arrive in many formats; PDFs dominate | A parser per format. PDFs split three ways: a text layer (extract it with layout: columns, headers, footers), scanned pages (OCR), and tables (keep a table whole, as a grid or markdown, never shred it across chunks) | A wrong parse is a silent retrieval failure: the fact exists, the text doesn't |
| Citations must point somewhere a person can check | Every chunk keeps its provenance: file, page, section heading, character or bounding-box span | "Page 14 of the vendor manual" is what makes an answer checkable |
| Millions of files, thousands changing a day | A queue of document jobs and a pool of workers. Each job is idempotent (keyed by a hash of the file's bytes), retried with backoff, and sent to a dead-letter queue after N failures. Unchanged files are skipped by hash; deleted files are removed everywhere, cached answers included | Partial failure is normal at volume; the pipeline must resume, not restart |
| The same text appears in many files (boilerplate, versions, copies) | Exact dedup by content hash, near-duplicate dedup by MinHash over word shingles | Duplicates waste index space and crowd the top results with one fact five times |
| Chunks lose their context ("it", "this model") | Structure-aware chunking (split on headings, keep tables whole), parent–child chunks (retrieve a small chunk, hand the model its parent section), and a short context line prepended to each chunk before embedding | Small chunks retrieve precisely; the model still needs the surrounding section to answer |
| Embedding millions of chunks | Batched embedding on GPU workers, cached by content hash so only changed text is re-embedded. Changing the embedding model means building a second index in the background and switching over once it is complete | Re-embedding is the most expensive ingest step; a model swap must never serve a half-migrated index (this repo already refuses mixed models) |

### 2. Retrieval has to find a needle in a much bigger haystack

At 96 sections, the right section is almost always in the top 5 by vector similarity alone. At millions of chunks,
thousands are "close enough", and three things become necessary.

- **An approximate index, tuned.** Exact nearest-neighbour search compares the query with every vector; that stops
  scaling. HNSW (the index this repo already uses, via pgvector) walks a graph instead. Its knobs trade recall for
  speed: `m` and `ef_construction` at build time, `ef_search` per query. Memory is the limit: vectors plus graph must
  fit in RAM, so production stores vectors in half precision or binary (then re-scores the top few hundred with full
  precision), and partitions or shards by tenant, date, or document type. Past a few tens of millions of vectors per
  node, teams move to engines built for it (Qdrant, Milvus, Vespa, OpenSearch) or disk-based indexes (DiskANN).
- **Two stages.** A wide first stage (hybrid: vector + keyword, top 100–200) for recall, then a cross-encoder or LLM
  reranker that reads each candidate against the question for precision. This repo measured a reranker lowering
  recall at 96 sections; at scale the first stage gets noisier and the reranker is how precision comes back. The plan
  below measures exactly that crossover.
- **Keyword search that weights rare words.** BM25 scores a term by how rare it is across the corpus (IDF), which is
  why "S16" or a cultivar name finds its document. Postgres's built-in `ts_rank_cd` has no IDF, which is why this
  repo's hybrid mode lost to vector search. Production uses a BM25 engine (Elasticsearch/OpenSearch, or `pg_search`
  inside Postgres) and fuses its ranking with the vector ranking.

Filters and permissions belong inside the search, not after it. If an index returns the top 5 and a permission check
then removes 4, the user gets 1 answerable chunk. Production pushes tenant, access-control and metadata filters into
the index query (pgvector 0.8 added iterative index scans for exactly this), and enforces tenant isolation in the
database itself (row-level security), so application bugs can't leak another customer's documents.

### 3. Questions get harder: multi-part and multi-hop

| Question shape | Example | What production does |
|---|---|---|
| Several independent questions in one message | "how long do they stay in the dome and when can i start feeding them" | Decompose into self-contained sub-questions with an LLM, resolving references ("them" → "tissue-culture plantlets"), retrieve for each in parallel, and give the model each sub-question's evidence. This repo's rule-based splitter is the zero-cost version; its known miss (m04) is the case the LLM version fixes |
| A question whose second step depends on the first | "which of my lights is strong enough for the plant that needs the most light" | Iterative retrieval: retrieve, read, write the next query from what was found, bounded to a few steps (the "agentic RAG" loop) |
| Every part must be answered or declared unknown | Any multi-part message | A coverage check: the answer lists each sub-question as answered from evidence or not covered, so a missed half is reported, never silently dropped |

### 4. Operations: the system must explain itself

- **Tracing per request** (OpenTelemetry): one trace per question with a span per stage (decompose, embed, retrieve,
  rerank, generate, verify), so "why was this answer slow or wrong" has an answer.
- **Verification before the answer leaves**: a faithfulness check that each sentence is supported by the section it
  cites (an NLI model or an LLM judge), and a refusal for the parts that aren't.
- **Documents are untrusted input.** At millions of files, some will contain text aimed at the model ("ignore your
  instructions"). Production treats retrieved text as data, flags suspicious chunks at ingest, and red-teams with
  poisoned documents, not only poisoned questions.
- **Evaluation at scale**: a fixed question set per domain, an LLM judge calibrated against human grades (measured
  agreement before it is trusted), online feedback, and a gate that blocks regressions. This repo has the gate and the
  human grades.
- **Cost and latency control**: caching (query embeddings, answers keyed by question and corpus version, provider
  prompt caching), routing easy questions to a smaller model, and load shedding (this repo already sheds at a
  concurrency limit).

---

## Part 2 — The over-build: what we build here, how each piece is proven

Constraints: local only, no paid APIs (generation stays on the `cc` backend), every care fact still comes from Keegan.
Synthetic or public data used for scale tests lives in separate tables and is never served as plant-care content.
Every track ends with a number in `eval/results/` or `eval/notes.md`, and every served change still goes through the
gate. Machine: i9-12900K (24 threads), 32 GB RAM, GTX 1080 Ti, 94 GB free disk.

| Track | What gets built | How it is proven | What production would swap in |
|---|---|---|---|
| **A. Multi-part questions** | LLM decomposition with reference resolution (`cc`), parallel retrieval per sub-question, per-part evidence in the prompt, and a coverage check (each part answered or declared not covered); genus filter inferred from the question | Eval v4 on dev against v3 through the gate; target m04 (the only partial); a blind sheet for Keegan; the added latency reported | A small fast model for decomposition; caching of decompositions |
| **B. Documents and PDFs** | A document pipeline: Postgres job queue (`FOR UPDATE SKIP LOCKED`), a worker pool, idempotency by file hash, retries and a dead-letter table; PDF parsing with page provenance (PyMuPDF), tables kept whole; structure-aware and parent–child chunking; exact and near-duplicate dedup | A "PDF edition" of Keegan's notes (each markdown doc rendered to PDF) ingested through the new path must match the markdown path's dev recall; citations carry page numbers; a throughput benchmark (documents per minute vs worker count); a kill-a-worker test showing resume without duplicates | S3 + SQS/Kafka, OCR service, autoscaled workers |
| **C. Millions of vectors** | A scale bench: 1M and 5M synthetic vectors clustered like real embeddings, HNSW `ef_search` sweep, half-precision and binary quantization with full-precision rescoring, partitioning; a "haystack" run that buries the 96 real sections among 100k+ real-text distractors (public text embedded locally) and re-runs the dev eval, first stage alone and with the reranker | Recall vs exact search, P50/P95 latency, index size and build time per setting; dev recall@5 at 96 sections vs in the haystack, with and without reranking (the crossover) | A dedicated vector engine or DiskANN past tens of millions; GPU embedding fleet |
| **D. Keyword search that scales** | BM25 with IDF (`pg_search` in a ParadeDB Postgres, same schema) fused with vector search | The dev eval in hybrid mode against today's vector mode, and in the haystack | Elasticsearch/OpenSearch or Vespa |
| **E. Access control and poisoned documents** | Tenants and document-level permissions enforced by row-level security on `chunks`, retrieval under a least-privilege role; poisoned-document probes added to the red team; ingest-time flagging of instruction-like text | Tests that one tenant never retrieves another's chunks (including through decomposition); red-team verdicts for poisoned documents | Identity-provider groups mapped to document ACLs |
| **F. Verification and tracing** | A faithfulness check: a local NLI model scores each answer sentence against its cited sections, unsupported sentences flagged; OpenTelemetry spans per stage, viewed in Jaeger (added to docker compose) | Agreement with Keegan's graded answers plus synthetic corrupted answers (a check that can't catch planted errors doesn't ship); a trace screenshot for the README | Managed tracing (Honeycomb, Datadog); an LLM judge calibrated on human grades |

Order: A first (it fixes the one partial answer and feeds the chat UI), then B and C (the "millions of files" story),
then D, E, F. Each track gets its own contract and punchlist before code, and an independent review before it is
called done.

### Decisions for Keegan

1. **Scope:** all six tracks, or a subset. My recommendation is A, B and C as the core, with D–F if time allows.
2. **Public text for the haystack:** a few hundred MB of public-domain text (for example a Wikipedia paragraph set)
   downloaded once and embedded locally. Synthetic vectors cover the speed numbers without it; the retrieval-quality
   crossover needs real text.
3. **GPU:** using the 1080 Ti for embedding means a CUDA build of PyTorch (a few GB) alongside the CPU one, if that
   build still supports the card's generation; otherwise CPU embedding, which turns the haystack build into hours
   instead of minutes.
