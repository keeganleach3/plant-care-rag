"""Local FastAPI service: POST /ask → answer + citations + retrieved chunks + stage timings.

  uv run uvicorn rag.api:app --host 127.0.0.1 --port 8000
The embedding model is loaded once at startup (≈11 s) and held in memory; per-request cost is embed + retrieve + generate.
Serving guards (docs/contracts/production-hardening.md): a checked connection pool; MAX_INFLIGHT concurrent generations,
then 503 busy; GET /healthz and /readyz; one JSON log line per /ask (request id, never the question text); optional
API_KEY bearer check on /ask.
"""
import hashlib
import hmac
import json
import logging
import re
import threading
import time
import uuid
from contextlib import asynccontextmanager, nullcontext
from typing import Literal

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

from rag import db, generate, llm, pipeline
from rag.config import settings
from rag.embed import Embedder

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
LOG_FIELDS = ("k", "mode", "decompose", "n_queries", "chunk_ids", "citations", "refused", "error_kind", "model", "usage",
              "question_chars", "question_sha")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=generate.MAX_QUESTION)
    k: int = 5
    mode: Literal["vector", "hybrid"] = "vector"
    genus: str | None = None
    decompose: bool = False


def create_app(conn=None, embedder=None, call=llm.call) -> FastAPI:
    """A given `conn` is used as-is (tests); otherwise startup opens a checked pool on DATABASE_URL."""
    cfg = settings(required=())
    inflight, api_key = int(cfg["MAX_INFLIGHT"]), cfg.get("API_KEY")
    slots = threading.BoundedSemaphore(inflight)
    state = {"pool": None, "embedder": embedder}

    @asynccontextmanager
    async def lifespan(_app):
        logging.basicConfig(format="%(message)s")  # no-op when the host already configured logging
        if not api_key:
            log.warning("API_KEY is not set: /ask is open to anyone who can reach this port")
        if conn is None:
            # autocommit: the connection is held through generation, so it must sit idle, not idle-in-transaction
            state["pool"] = ConnectionPool(settings()["DATABASE_URL"], kwargs={"autocommit": True}, min_size=1,
                                           max_size=inflight + 2, configure=db.register,
                                           check=ConnectionPool.check_connection, open=True)
        if state["embedder"] is None:
            t = time.perf_counter()
            state["embedder"] = Embedder(cfg["EMBED_MODEL"])
            print(f"embedding model {state['embedder'].name} loaded in {time.perf_counter() - t:.1f}s", flush=True)
        yield
        if state["pool"] is not None:
            state["pool"].close()

    app = FastAPI(title="plant-care-rag", lifespan=lifespan)

    def borrow():
        return nullcontext(conn) if conn is not None else state["pool"].connection()

    def authorize(authorization: str = Header("")):
        # Bytes, not str: compare_digest raises TypeError on non-ASCII str, turning a bad header into a 500.
        if api_key and not hmac.compare_digest(authorization.encode("latin-1"), f"Bearer {api_key}".encode()):
            raise HTTPException(401, "missing or invalid API key", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        try:
            with borrow() as c:
                n = c.execute("SELECT count(*) FROM chunks").fetchone()[0]
            failed = [] if n else ["chunks"]
        except psycopg.Error:
            n, failed = None, ["db"]
        if state["embedder"] is None:
            failed.append("embedder")
        if failed:
            return JSONResponse({"status": "not ready", "failed": failed}, status_code=503)
        return {"status": "ready", "chunks": n}

    @app.post("/ask", dependencies=[Depends(authorize)])
    def ask(req: AskRequest, request: Request):
        request.state.log = {"k": req.k, "mode": req.mode, "decompose": req.decompose, "question_chars": len(req.question),
                             "question_sha": hashlib.sha256(req.question.encode()).hexdigest()[:12]}
        if not slots.acquire(blocking=False):
            raise HTTPException(503, "busy", headers={"Retry-After": "5"})
        try:
            with borrow() as c:
                out = pipeline.ask(c, state["embedder"], req.question, k=req.k, mode=req.mode, genus=req.genus,
                                   decompose=req.decompose, call=call)
        finally:
            slots.release()
        err = out.pop("error")
        request.state.log |= {"k": out["params"]["k"], "n_queries": len(out["queries"]),
                              "chunk_ids": [h["chunk_id"] for h in out["chunks"]], "citations": out.get("citations"),
                              "refused": out.get("refused"), "error_kind": err and err["kind"], "model": out["model"],
                              "usage": err["usage"] if err else out["usage"]}
        if err:
            raise HTTPException(status_code=502, detail=f"{err['kind']}: {err['detail']}")
        return out

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id", "")
        if not REQUEST_ID.fullmatch(rid):
            rid = uuid.uuid4().hex
        t = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("unhandled error, request_id=%s", rid)
            response = JSONResponse({"detail": "internal error"}, status_code=500)
        response.headers["X-Request-ID"] = rid
        if request.scope.get("endpoint") is ask:
            line = {"request_id": rid, "status": response.status_code, "total_ms": round((time.perf_counter() - t) * 1000, 1)}
            log.info(json.dumps(line | dict.fromkeys(LOG_FIELDS) | getattr(request.state, "log", {}), default=str))
        return response

    return app


app = create_app()
