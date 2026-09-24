-- chunks.embed_model: the model that produced each vector, so a query embedded with another model is refused instead of
-- silently mis-ranked (contract production-hardening §2). Idempotent and atomic: docker runs it once on a fresh volume,
-- tests/conftest.py re-applies it every session.
-- Backfill: bge-base is the only model ingested before 002 (proven on dev by re-embedding sample chunks, cosine > 0.999).
-- Down: ALTER TABLE chunks DROP COLUMN embed_model;   -- re-ingest restores the data
BEGIN;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embed_model text;
UPDATE chunks SET embed_model = 'BAAI/bge-base-en-v1.5' WHERE embed_model IS NULL;
ALTER TABLE chunks ALTER COLUMN embed_model SET NOT NULL;
COMMIT;
