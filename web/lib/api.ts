// Browser side: calls the app's own /api routes, never the RAG service directly.
import type { AskError, AskErrorKind, AskResponse, Genus, Sources } from "./types";

export const MAX_QUESTION = 500; // rag/generate.py MAX_QUESTION

export class ApiError extends Error {
  constructor(readonly info: AskError) {
    super(info.kind);
  }
}

const SERVICE_503 = new Set(["busy", "db", "embed_model", "unreachable"]);

async function errorFrom(res: Response): Promise<ApiError> {
  let detail = "";
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    // no JSON body: the status alone decides the kind
  }
  const kind: AskErrorKind =
    res.status === 503 && SERVICE_503.has(detail)
      ? (detail as AskErrorKind)
      : res.status === 504
        ? "timeout"
        : res.status === 502
          ? "generation"
          : res.status === 401
            ? "rejected"
            : "unknown";
  const retryAfter = Number(res.headers.get("retry-after")) || undefined;
  return new ApiError({ kind, detail, status: res.status, retryAfter });
}

async function call(url: string, init: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    if (init.signal?.aborted) throw err;
    throw new ApiError({ kind: "unreachable", detail: "web server", status: 0 });
  }
  if (!res.ok) throw await errorFrom(res);
  return res;
}

export async function ask(question: string, genus: Genus | null, signal?: AbortSignal): Promise<AskResponse> {
  const res = await call("/api/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question, genus }),
    signal,
  });
  return res.json();
}

export async function fetchSources(signal?: AbortSignal): Promise<Sources> {
  return (await call("/api/sources", { signal })).json();
}

/** The error as ApiError info; anything else (a bug, a bad JSON body) becomes kind "unknown". */
export function toAskError(err: unknown): AskError {
  return err instanceof ApiError ? err.info : { kind: "unknown", detail: String(err), status: 0 };
}
