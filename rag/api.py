"""Local FastAPI service: POST /ask → answer + citations + retrieved chunks + stage timings.

  uv run uvicorn rag.api:app --host 127.0.0.1 --port 8000
The embedding model is loaded once at startup (≈11 s) and held in memory; per-request cost is embed + retrieve + generate.
"""
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag import db, generate, llm, retrieve
from rag.config import GENERA, settings
from rag.embed import Embedder


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=generate.MAX_QUESTION)
    k: int = 5
    mode: Literal["vector", "hybrid"] = "vector"
    genus: str | None = None


def create_app(conn=None, embedder=None, call=llm.call) -> FastAPI:
    state = {"conn": conn, "embedder": embedder}

    @asynccontextmanager
    async def lifespan(_app):
        if state["conn"] is None:
            state["conn"] = db.connect()
        if state["embedder"] is None:
            t = time.perf_counter()
            state["embedder"] = Embedder(settings()["EMBED_MODEL"])
            print(f"embedding model {state['embedder'].name} loaded in {time.perf_counter() - t:.1f}s", flush=True)
        yield

    app = FastAPI(title="plant-care-rag", lifespan=lifespan)

    @app.post("/ask")
    def ask(req: AskRequest):
        k = max(1, min(req.k, 20))
        genus = req.genus if req.genus in GENERA else None
        emb, conn = state["embedder"], state["conn"]
        t0 = time.perf_counter()
        q = emb.embed_query(req.question)
        t1 = time.perf_counter()
        hits = retrieve.search(conn, emb, req.question, k=k, mode=req.mode, genus=genus, query_embedding=q)
        t2 = time.perf_counter()
        try:
            ans = generate.answer(req.question, hits, call=call)
        except (generate.GenerationError, llm.LLMError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        t3 = time.perf_counter()
        ms = lambda a, b: round((b - a) * 1000, 1)
        return {
            "answer": ans.answer, "citations": ans.citations, "refused": ans.refused,
            "chunks": [asdict(h) for h in hits],
            "params": {"k": k, "mode": req.mode, "genus": genus},
            "model": ans.model, "usage": ans.usage,
            "timings": {"embed_ms": ms(t0, t1), "retrieve_ms": ms(t1, t2), "generate_ms": ms(t2, t3), "total_ms": ms(t0, t3)},
        }

    return app


app = create_app()
