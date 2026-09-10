CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id          serial PRIMARY KEY,
  slug        text UNIQUE NOT NULL,
  genus       text NOT NULL,          -- philodendron | anthurium | monstera | alocasia | general
  topic       text NOT NULL,          -- acclimation | humidity | light | substrate-water | pests | quirks | troubleshooting
  title       text NOT NULL,
  source_path text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
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

CREATE INDEX chunks_hnsw  ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_tsv   ON chunks USING gin (tsv);
CREATE INDEX chunks_genus ON chunks (genus);

-- Hybrid retrieval: reciprocal rank fusion over the top-50 vector hits and top-50 full-text hits.
CREATE FUNCTION hybrid_search(query_text text, query_embedding vector(768), k int DEFAULT 5, genus_filter text DEFAULT NULL)
RETURNS TABLE(chunk_id text, score float) AS $$
  WITH vec AS (
    SELECT c.chunk_id, row_number() OVER (ORDER BY c.embedding <=> query_embedding) AS rnk
    FROM chunks c
    WHERE genus_filter IS NULL OR c.genus = genus_filter OR c.genus = 'general'
    ORDER BY c.embedding <=> query_embedding LIMIT 50
  ),
  fts AS (
    SELECT c.chunk_id, row_number() OVER (ORDER BY ts_rank_cd(c.tsv, plainto_tsquery('english', query_text)) DESC) AS rnk
    FROM chunks c
    WHERE c.tsv @@ plainto_tsquery('english', query_text)
      AND (genus_filter IS NULL OR c.genus = genus_filter OR c.genus = 'general')
    LIMIT 50
  )
  SELECT COALESCE(vec.chunk_id, fts.chunk_id) AS chunk_id,
         COALESCE(1.0 / (60 + vec.rnk), 0) + COALESCE(1.0 / (60 + fts.rnk), 0) AS score
  FROM vec FULL OUTER JOIN fts USING (chunk_id)
  ORDER BY score DESC LIMIT k;
$$ LANGUAGE sql STABLE;
