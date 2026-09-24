"""Local FastAPI service: POST /ask → answer + citations + retrieved chunks + stage timings.

  uv run uvicorn rag.api:app --host 127.0.0.1 --port 8000
The embedding model is loaded once at startup (≈11 s) and held in memory; per-request cost is embed + retrieve + generate.
"""
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag import db, generate, llm, pipeline
from rag.config import settings
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
        out = pipeline.ask(state["conn"], state["embedder"], req.question, k=req.k, mode=req.mode, genus=req.genus, call=call)
        if err := out.pop("error"):
            raise HTTPException(status_code=502, detail=f"{err['kind']}: {err['detail']}")
        return out

    return app


app = create_app()
