"""Retrieval: vector (cosine) or hybrid (RRF over vector + full-text, see db/init/001_schema.sql)."""
from dataclasses import dataclass

from rag.embed import Embedder

MODES = ("vector", "hybrid")
_COLS = "c.chunk_id, c.content, c.heading, c.genus, c.topic"


@dataclass
class Hit:
    chunk_id: str
    content: str
    heading: str
    genus: str
    topic: str
    score: float


def search(conn, embedder: Embedder, question: str, k: int = 5, mode: str = "vector", genus: str | None = None) -> list[Hit]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    k = max(1, min(int(k), 20))
    q = embedder.embed_query(question)
    if mode == "vector":
        rows = conn.execute(
            f"""SELECT {_COLS}, 1 - (c.embedding <=> %(q)s::vector) AS score FROM chunks c
                WHERE %(g)s::text IS NULL OR c.genus = %(g)s OR c.genus = 'general'
                ORDER BY c.embedding <=> %(q)s::vector LIMIT %(k)s""",
            {"q": q, "g": genus, "k": k},
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT {_COLS}, h.score FROM hybrid_search(%(t)s, %(q)s::vector, %(k)s, %(g)s) h
                JOIN chunks c USING (chunk_id) ORDER BY h.score DESC""",
            {"t": question, "q": q, "k": k, "g": genus},
        ).fetchall()
    return [Hit(*r[:5], float(r[5])) for r in rows]
