-- Idempotent: docker runs db/init/*.sql in order on a fresh volume; tests/conftest.py re-applies them every session.
-- keegan-code:allow rls — single-tenant public corpus: every row is readable by the app and there are no per-user rows (contract-pipeline §3)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id          serial PRIMARY KEY,
  slug        text UNIQUE NOT NULL,
  genus       text NOT NULL,          -- philodendron | anthurium | monstera | alocasia | general
  topic       text NOT NULL,          -- acclimation | humidity | light | substrate-water | pests | quirks | troubleshooting
  title       text NOT NULL,
  source_path text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id          serial PRIMARY KEY,
  document_id int NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_id    text UNIQUE NOT NULL,   -- <doc-slug>#<section-slug>[-n]; stable across re-ingest
  genus       text NOT NULL,
  topic       text NOT NULL,
  heading     text NOT NULL,
  content     text NOT NULL,
  tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  embedding   vector(768)             -- bge-base-en-v1.5 and nomic-embed-text-v1.5 are both 768-dim
);

CREATE INDEX IF NOT EXISTS chunks_hnsw  ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv   ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_genus ON chunks (genus);

-- Hybrid retrieval: reciprocal rank fusion over the top-50 vector hits and top-50 full-text hits.
-- The full-text leg ORs the question's lexemes: plainto_tsquery ANDs them, and a whole customer question almost never
-- has every word in one section (1 of 38 eval questions matched anything, so hybrid silently returned the vector ranking).
-- A stopword-only question yields a NULL tsquery, which matches nothing.
CREATE OR REPLACE FUNCTION hybrid_search(query_text text, query_embedding vector(768), k int DEFAULT 5, genus_filter text DEFAULT NULL)
RETURNS TABLE(chunk_id text, score float) AS $$
  WITH q AS (
    SELECT to_tsquery('simple', nullif(array_to_string(ARRAY(
             SELECT quote_literal(l) FROM unnest(tsvector_to_array(to_tsvector('english', query_text))) l), ' | '), '')) AS tsq
  ),
  vec AS (
    SELECT c.chunk_id, row_number() OVER (ORDER BY c.embedding <=> query_embedding) AS rnk
    FROM chunks c
    WHERE genus_filter IS NULL OR c.genus = genus_filter OR c.genus = 'general'
    ORDER BY c.embedding <=> query_embedding LIMIT 50
  ),
  fts AS (
    SELECT c.chunk_id, row_number() OVER (ORDER BY ts_rank_cd(c.tsv, q.tsq) DESC) AS rnk
    FROM chunks c, q
    WHERE c.tsv @@ q.tsq
      AND (genus_filter IS NULL OR c.genus = genus_filter OR c.genus = 'general')
    ORDER BY ts_rank_cd(c.tsv, q.tsq) DESC LIMIT 50
  )
  SELECT COALESCE(vec.chunk_id, fts.chunk_id) AS chunk_id,
         COALESCE(1.0 / (60 + vec.rnk), 0) + COALESCE(1.0 / (60 + fts.rnk), 0) AS score
  FROM vec FULL OUTER JOIN fts USING (chunk_id)
  ORDER BY score DESC LIMIT k;
$$ LANGUAGE sql STABLE;
