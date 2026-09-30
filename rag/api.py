"""Local FastAPI service: POST /ask → answer + citations + retrieved chunks + stage timings; GET /sources → every indexed
section, grouped by note (docs/contracts/chat-ui-api.md).

  uv run uvicorn rag.api:app --host 127.0.0.1 --port 8000
The embedding model is loaded once at startup (≈11 s) and held in memory; per-request cost is embed + retrieve + generate.
Serving guards (docs/contracts/production-hardening.md): a checked connection pool with connect and statement timeouts;
MAX_INFLIGHT concurrent generations, then 503 busy; a 4096-byte body cap; GET /healthz and /readyz; one JSON log line per
/ask (request id, never the question text); API_KEY bearer check on /ask and /sources (32+ chars, required on the paid api
backend; set, it also hides /docs and the OpenAPI schema).
"""
import hashlib
import hmac
import json
import logging
import re
import shutil
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
from rag.config import ConfigError, settings
from rag.embed import Embedder

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
READY_TIMEOUT_S = 2  # a borrow answers fast or says "db"; the pool's 30 s default outlives any probe or client
# autocommit: a connection is held through generation, so it must sit idle, not idle-in-transaction. The timeouts bound a
# blackholed host and a runaway query, either of which would otherwise hold a MAX_INFLIGHT slot.
DB_KWARGS = {"autocommit": True, "connect_timeout": 5, "options": "-c statement_timeout=10s"}
MAX_BODY = 4096  # bytes; a 500-char question fits with room to spare
LOG_FIELDS = ("k", "mode", "decompose", "n_queries", "chunk_ids", "citations", "refused", "error_kind", "error_detail", "model", "usage",
              "question_chars", "question_sha")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=generate.MAX_QUESTION)
    k: int = 5
    mode: Literal["vector", "hybrid"] = "vector"
    genus: str | None = None
    decompose: bool = True  # served since eval v2 (eval/results/v2/change.md)


def create_app(conn=None, embedder=None, call=llm.call) -> FastAPI:
    """A given `conn` is used as-is (tests); otherwise startup opens a checked pool on DATABASE_URL."""
    cfg = settings(required=())
    inflight, api_key, want = int(cfg["MAX_INFLIGHT"]), cfg.get("API_KEY"), {cfg["EMBED_MODEL"]}
    slots = threading.BoundedSemaphore(inflight)
    # checked: stored vectors match EMBED_MODEL (vectors from another model rank garbage with no error)
    state = {"pool": None, "embedder": embedder, "checked": False}

    @asynccontextmanager
    async def lifespan(_app):
        logging.basicConfig(format="%(message)s")  # no-op when the host already configured logging
        if api_key and len(api_key) < 32:
            raise ConfigError("API_KEY must be at least 32 characters")  # never the key itself
        if not api_key:
            if cfg["LLM_BACKEND"] == "api":  # anyone who reaches the port would spend the Anthropic budget
                raise ConfigError("API_KEY is required with LLM_BACKEND=api: /ask would be open on the paid backend")
            log.warning("API_KEY is not set: /ask is open to anyone who can reach this port")
        if conn is None:
            state["pool"] = ConnectionPool(settings()["DATABASE_URL"], kwargs=DB_KWARGS, min_size=1, max_size=inflight + 2,
                                           configure=db.register, check=ConnectionPool.check_connection, open=True)
        try:
            try:
                with borrow(READY_TIMEOUT_S) as c:
                    models = db.embed_models(c)
            except psycopg.OperationalError:  # unreachable, not wrong: any other psycopg.Error (schema) stops startup
                log.warning("database unreachable at startup: /readyz reports db and the embed_model check runs on the first /ask")
            else:
                if models - want:
                    raise RuntimeError(f"chunks are embedded with {sorted(models)} but EMBED_MODEL is {cfg['EMBED_MODEL']!r}; "
                                       "re-ingest or set EMBED_MODEL to match")
                state["checked"] = True
            if state["embedder"] is None:
                t = time.perf_counter()
                state["embedder"] = Embedder(cfg["EMBED_MODEL"])
                print(f"embedding model {state['embedder'].name} loaded in {time.perf_counter() - t:.1f}s", flush=True)
            yield
        finally:
            if state["pool"] is not None:
                state["pool"].close()

    # a keyed deployment does not publish its API surface; local runs keep the interactive docs
    app = FastAPI(title="plant-care-rag", lifespan=lifespan, docs_url=None if api_key else "/docs",
                  redoc_url=None if api_key else "/redoc", openapi_url=None if api_key else "/openapi.json")

    def borrow(timeout=None):
        return nullcontext(conn) if conn is not None else state["pool"].connection(timeout=timeout)

    def authorize(authorization: str = Header("")):
        # Bytes, not str: compare_digest raises TypeError on non-ASCII str, turning a bad header into a 500.
        if api_key and not hmac.compare_digest(authorization.encode("latin-1"), f"Bearer {api_key}".encode()):
            raise HTTPException(401, "missing or invalid API key", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        failed = []
        try:
            with borrow(READY_TIMEOUT_S) as c:
                n = c.execute("SELECT count(*) FROM chunks").fetchone()[0]
                models = db.embed_models(c)
            if not n:
                failed.append("chunks")
            elif models != want:
                failed.append("embed_model")
        except psycopg.OperationalError:  # unreachable, pool exhausted, or statement timeout
            n, failed = None, ["db"]
        except psycopg.Error:  # reachable, but not the schema this code reads (e.g. no embed_model column)
            n, failed = None, ["schema"]
        if state["embedder"] is None:
            failed.append("embedder")
        if cfg["LLM_BACKEND"] == "cc" and shutil.which("claude") is None:  # every generation would fail cli_error
            failed.append("llm")
        if failed:
            return JSONResponse({"status": "not ready", "failed": failed}, status_code=503)
        return {"status": "ready", "chunks": n}

    @app.get("/sources", dependencies=[Depends(authorize)])
    def sources():
        """Every indexed section, grouped by note: notes by genus then title, sections in ingest order."""
        try:
            with borrow(READY_TIMEOUT_S) as c:
                rows = c.execute("""SELECT d.slug, d.title, d.genus, d.topic, c.chunk_id, c.heading, c.content
                                    FROM documents d JOIN chunks c ON c.document_id = d.id
                                    ORDER BY d.genus, d.title, c.id""").fetchall()
        except psycopg.OperationalError:  # unreachable, every connection held past the wait, or statement timeout
            raise HTTPException(503, "db", headers={"Retry-After": "5"})
        notes = {}
        for slug, title, genus, topic, chunk_id, heading, content in rows:
            note = notes.setdefault(slug, {"slug": slug, "title": title, "genus": genus, "topic": topic, "sections": []})
            note["sections"].append({"chunk_id": chunk_id, "heading": heading, "content": content})
        return {"embed_model": cfg["EMBED_MODEL"], "notes": list(notes.values())}

    @app.post("/ask", dependencies=[Depends(authorize)])
    def ask(req: AskRequest, request: Request):
        """Answer from the corpus with validated citations, the retrieved chunks and stage timings.

        `chunks[].score` is cosine similarity in plain vector search, and a reciprocal-rank-fusion (RRF) score in hybrid
        mode or when decompose splits the message into several questions; the two scales are not comparable."""
        request.state.log = {"k": req.k, "mode": req.mode, "decompose": req.decompose, "question_chars": len(req.question),
                             "question_sha": hashlib.sha256(req.question.encode()).hexdigest()[:12]}
        if not slots.acquire(blocking=False):
            raise HTTPException(503, "busy", headers={"Retry-After": "5"})
        try:
            with borrow(READY_TIMEOUT_S) as c:
                if not state["checked"]:  # deferred: the database was unreachable at startup
                    if db.embed_models(c) - want:
                        raise HTTPException(503, "embed_model")
                    state["checked"] = True
                out = pipeline.ask(c, state["embedder"], req.question, k=req.k, mode=req.mode, genus=req.genus,
                                   decompose=req.decompose, call=call)
        except psycopg.OperationalError:  # includes PoolTimeout: unreachable, or every connection held past the wait
            raise HTTPException(503, "db", headers={"Retry-After": "5"})
        finally:
            slots.release()
        err = out.pop("error")
        request.state.log |= {"k": out["params"]["k"], "n_queries": len(out["queries"]),
                              "chunk_ids": [h["chunk_id"] for h in out["chunks"]], "citations": out.get("citations"),
                              "refused": out.get("refused"), "error_kind": err and err["kind"],
                              # CLI stderr or model output can quote the question back
                              "error_detail": err and err["detail"].replace(req.question, "[question]"), "model": out["model"],
                              "usage": err["usage"] if err else out["usage"]}
        if err:  # the caller gets the kind; the detail (CLI stderr, cited ids) stays in the server log
            raise HTTPException(status_code=502, detail=err["kind"])
        return out

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id", "")
        if not REQUEST_ID.fullmatch(rid):
            rid = uuid.uuid4().hex
        t = time.perf_counter()
        # the path the router matches: uvicorn --root-path prefixes scope["path"]
        is_ask = request.method == "POST" and request.scope["path"].removeprefix(request.scope.get("root_path", "")) == "/ask"
        length = request.headers.get("content-length", "")
        # Checked before anything reads the body. Transfer-Encoding beats Content-Length (RFC 9112 6.3; h11 under uvicorn
        # frames by it), so a chunked body has no length to trust, whatever Content-Length says.
        if is_ask and ("transfer-encoding" in request.headers or not length.isdecimal()):
            response = JSONResponse({"detail": "Content-Length required"}, status_code=411)
        elif is_ask and int(length) > MAX_BODY:
            response = JSONResponse({"detail": f"request body over {MAX_BODY} bytes"}, status_code=413)
        else:
            try:
                response = await call_next(request)
            except Exception:
                log.exception("unhandled error, request_id=%s", rid)
                response = JSONResponse({"detail": "internal error"}, status_code=500)
        response.headers["X-Request-ID"] = rid
        if is_ask:
            line = {"request_id": rid, "status": response.status_code, "total_ms": round((time.perf_counter() - t) * 1000, 1)}
            log.info(json.dumps(line | dict.fromkeys(LOG_FIELDS) | getattr(request.state, "log", {}), default=str))
        return response

    return app


app = create_app()
