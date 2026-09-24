"""Retrieval: vector (cosine) or hybrid (RRF over vector + full-text, see db/init/001_schema.sql).
With decomposition, a message holding several questions is searched whole and per question, and the rankings fused."""
import re
from dataclasses import dataclass, replace

from rag.embed import Embedder

MODES = ("vector", "hybrid")
_COLS = "c.chunk_id, c.content, c.heading, c.genus, c.topic"
POOL = 20        # depth of each ranking that gets fused
RRF_C = 60       # the reciprocal-rank constant hybrid_search uses
MIN_WORDS = 4    # a shorter fragment ("is that bad") is too thin to search on its own
MAX_CLAUSES = 4  # a message with more turns into an unwieldy fan-out of searches
_ASKS = r"how|what|whats|what's|when|where|which|why|who|can|could|should|would|will|do|does|is|are"
_JOIN = re.compile(rf",?\s+(?:and|or|also|plus)\s+(?=(?:{_ASKS})\b)", re.IGNORECASE)


@dataclass
class Hit:
    chunk_id: str
    content: str
    heading: str
    genus: str
    topic: str
    score: float


def search(conn, embedder: Embedder, question: str, k: int = 5, mode: str = "vector", genus: str | None = None,
           query_embedding: list[float] | None = None) -> list[Hit]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    k = max(1, min(int(k), 20))
    q = query_embedding if query_embedding is not None else embedder.embed_query(question)
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


def clauses(question: str) -> list[str]:
    """The separate questions in one message: split at '?' and where and/or/also/plus opens a new question
    ("... how long in the dome and when do i start feeding"). [] when fewer than two are long enough to search."""
    parts = [p.strip(" ,.;") for s in re.split(r"\?+", question) for p in _JOIN.split(s)]
    parts = [p for p in parts if len(p.split()) >= MIN_WORDS][:MAX_CLAUSES]
    return parts if len(parts) > 1 else []


def fuse(rankings: list[list[Hit]], k: int) -> list[Hit]:
    """Reciprocal rank fusion; a tie keeps first-seen order, so the whole question's ranking (passed first) wins it."""
    score, first = {}, {}
    for ranking in rankings:
        for rank, h in enumerate(ranking, 1):
            score[h.chunk_id] = score.get(h.chunk_id, 0.0) + 1 / (RRF_C + rank)
            first.setdefault(h.chunk_id, h)
    order = sorted(first, key=lambda cid: -score[cid])  # stable: dict order is first-seen order
    return [replace(first[cid], score=score[cid]) for cid in order[:k]]


def search_all(conn, queries: list[str], embeddings: list[list[float]], k: int = 5, mode: str = "vector",
               genus: str | None = None) -> list[Hit]:
    """One query is plain search; several (the whole question first, then its clauses) are fused."""
    if len(queries) == 1:
        return search(conn, None, queries[0], k=k, mode=mode, genus=genus, query_embedding=embeddings[0])
    return fuse([search(conn, None, q, k=POOL, mode=mode, genus=genus, query_embedding=e)
                 for q, e in zip(queries, embeddings)], max(1, min(int(k), 20)))
