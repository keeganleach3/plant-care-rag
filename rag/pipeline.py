"""One question through the served path: embed → retrieve → generate, with stage timings.
The API and the eval runner both call this, so the eval measures exactly what /ask serves."""
import time
from dataclasses import asdict

from rag import generate, llm, retrieve
from rag.config import GENERA


def ask(conn, embedder, question: str, *, k: int = 5, mode: str = "vector", genus: str | None = None, decompose: bool = False,
        call=llm.call, model: str = generate.MODEL, effort: str = generate.EFFORT) -> dict:
    """A generation failure comes back as `error: {kind, detail, attempts, usage}` with the retrieved chunks,
    the requested model and the timings intact. `queries` is what was searched: the question, then its clauses."""
    k = max(1, min(k, 20))
    genus = genus if genus in GENERA else None
    queries = [question, *retrieve.clauses(question)] if decompose else [question]
    t0 = time.perf_counter()
    vecs = [embedder.embed_query(q) for q in queries]
    t1 = time.perf_counter()
    hits = retrieve.search_all(conn, queries, vecs, k=k, mode=mode, genus=genus)
    t2 = time.perf_counter()
    out = {"params": {"k": k, "mode": mode, "genus": genus, "decompose": decompose}, "queries": queries,
           "chunks": [asdict(h) for h in hits], "model": model, "error": None}
    try:
        ans = generate.answer(question, hits, call=call, model=model, effort=effort)
        out |= {"answer": ans.answer, "citations": ans.citations, "refused": ans.refused, "model": ans.model, "usage": ans.usage}
    except (generate.GenerationError, llm.LLMError) as exc:
        out["error"] = {"kind": exc.kind, "detail": exc.detail,
                        "attempts": getattr(exc, "attempts", None), "usage": getattr(exc, "usage", None)}
    t3 = time.perf_counter()
    ms = lambda a, b: round((b - a) * 1000, 1)
    out["timings"] = {"embed_ms": ms(t0, t1), "retrieve_ms": ms(t1, t2), "generate_ms": ms(t2, t3), "total_ms": ms(t0, t3)}
    return out
