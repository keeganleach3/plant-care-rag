"""One question through the served path: embed → retrieve → generate, with stage timings.
The API and the eval runner both call this, so the eval measures exactly what /ask serves."""
import time
from dataclasses import asdict

from rag import generate, llm, retrieve
from rag.config import GENERA


def ask(conn, embedder, question: str, *, k: int = 5, mode: str = "vector", genus: str | None = None, call=llm.call,
        model: str = generate.MODEL, effort: str = generate.EFFORT) -> dict:
    """A generation failure comes back as `error: {kind, detail, attempts, usage}` with the retrieved chunks,
    the requested model and the timings intact."""
    k = max(1, min(k, 20))
    genus = genus if genus in GENERA else None
    t0 = time.perf_counter()
    q = embedder.embed_query(question)
    t1 = time.perf_counter()
    hits = retrieve.search(conn, embedder, question, k=k, mode=mode, genus=genus, query_embedding=q)
    t2 = time.perf_counter()
    out = {"params": {"k": k, "mode": mode, "genus": genus}, "chunks": [asdict(h) for h in hits], "model": model, "error": None}
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
