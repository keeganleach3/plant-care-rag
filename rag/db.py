import psycopg
from pgvector.psycopg import register_vector

from rag.chunker import Chunk, Doc
from rag.config import settings


def connect() -> psycopg.Connection:
    conn = psycopg.connect(settings()["DATABASE_URL"], autocommit=True)
    register(conn)
    return conn


def register(conn: psycopg.Connection) -> None:
    register_vector(conn)


def upsert_document(conn, doc: Doc) -> int:
    return conn.execute(
        """INSERT INTO documents (slug, genus, topic, title, source_path) VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (slug) DO UPDATE SET genus=EXCLUDED.genus, topic=EXCLUDED.topic, title=EXCLUDED.title,
             source_path=EXCLUDED.source_path, ingested_at=now()
           RETURNING id""",
        (doc.slug, doc.genus, doc.topic, doc.title, doc.source_path),
    ).fetchone()[0]


def upsert_chunks(conn, document_id: int, chunks: list[Chunk], embeddings: list[list[float]], embed_model: str) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO chunks (document_id, chunk_id, genus, topic, heading, content, embedding, embed_model)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (chunk_id) DO UPDATE SET document_id=EXCLUDED.document_id, genus=EXCLUDED.genus,
                 topic=EXCLUDED.topic, heading=EXCLUDED.heading, content=EXCLUDED.content, embedding=EXCLUDED.embedding,
                 embed_model=EXCLUDED.embed_model""",
            [(document_id, c.chunk_id, c.genus, c.topic, c.heading, c.content, e, embed_model) for c, e in zip(chunks, embeddings)],
        )


def embed_models(conn) -> set[str]:
    """Models behind the stored vectors; a query embedded with any other model ranks garbage without an error."""
    return {m for (m,) in conn.execute("SELECT DISTINCT embed_model FROM chunks").fetchall()}


def prune(conn, keep_chunk_ids: set[str], keep_doc_slugs: set[str]) -> int:
    n = conn.execute("DELETE FROM chunks WHERE NOT (chunk_id = ANY(%s))", (list(keep_chunk_ids),)).rowcount
    conn.execute("DELETE FROM documents WHERE NOT (slug = ANY(%s))", (list(keep_doc_slugs),))
    return n
