// Server side only: the route handlers in app/api call the RAG service through this. RAG_API_KEY has no NEXT_PUBLIC_
// prefix, so Next never inlines it into a client bundle, and no response carries it (docs/contracts/chat-ui-api.md).
import "server-only";

const BASE = (process.env.RAG_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const KEY = process.env.RAG_API_KEY || undefined;
// Checked here so a bad value fails with this message, not inside Headers.set, whose error quotes the value.
if (KEY && !/^[\x21-\x7e]+$/.test(KEY)) {
  throw new Error("RAG_API_KEY has characters an HTTP header can't carry (a space, quote or line break?)");
}

// This proxy adds the key, so it serves only this machine's own page: the names it is reached by locally (a rebound DNS
// name fails), same-origin fetches (a cross-site page's fetch fails), and JSON bodies (a cross-site "simple" POST can't
// send one without a preflight, which nothing here answers).
const LOCAL_HOST = /^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/;

export function refuse(req: Request): Response | null {
  const host = req.headers.get("host") ?? "";
  const site = req.headers.get("sec-fetch-site");
  const origin = req.headers.get("origin");
  const foreign = (o: string) => URL.parse(o)?.host !== host; // "null" (sandboxed frames, file://) parses to null
  if (!LOCAL_HOST.test(host) || (site && site !== "same-origin") || (origin && foreign(origin))) {
    return Response.json({ detail: "forbidden" }, { status: 403 });
  }
  if (req.method === "POST" && !req.headers.get("content-type")?.startsWith("application/json")) {
    return Response.json({ detail: "content-type must be application/json" }, { status: 415 });
  }
  return null;
}

export async function forward(path: string, init: { method: "GET" | "POST"; body?: string }, timeoutMs: number) {
  const rid = crypto.randomUUID().replaceAll("-", "");
  const headers = new Headers({ "x-request-id": rid });
  if (init.body !== undefined) headers.set("content-type", "application/json");
  if (KEY) headers.set("authorization", `Bearer ${KEY}`);
  let res: Response;
  try {
    // A string body gets a Content-Length, which the service requires (411 without one).
    res = await fetch(BASE + path, { ...init, headers, cache: "no-store", signal: AbortSignal.timeout(timeoutMs) });
  } catch (err) {
    const timedOut = err instanceof DOMException && err.name === "TimeoutError";
    return Response.json(
      { detail: timedOut ? "timeout" : "unreachable" },
      { status: timedOut ? 504 : 503, headers: { "x-request-id": rid } },
    );
  }
  const out = new Headers({
    "content-type": res.headers.get("content-type") ?? "application/json",
    "x-request-id": res.headers.get("x-request-id") ?? rid,
  });
  const retryAfter = res.headers.get("retry-after");
  if (retryAfter) out.set("retry-after", retryAfter);
  return new Response(res.body, { status: res.status, headers: out });
}

/** The request body as text, or null once it passes `cap` bytes (read no further). */
export async function readCapped(req: Request, cap: number): Promise<string | null> {
  if (Number(req.headers.get("content-length") ?? 0) > cap) return null;
  if (!req.body) return "";
  const reader = req.body.getReader();
  const parts: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > cap) {
      await reader.cancel();
      return null;
    }
    parts.push(value);
  }
  return new TextDecoder().decode(Buffer.concat(parts));
}
