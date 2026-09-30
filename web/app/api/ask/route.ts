import { forward, readCapped } from "@/lib/upstream";

const MAX_BODY = 4096; // bytes, the service's own cap (rag/api.py)
const TIMEOUT_MS = 150_000; // past the service's 120 s generation timeout

export async function POST(req: Request) {
  const body = await readCapped(req, MAX_BODY);
  if (body === null) return Response.json({ detail: `request body over ${MAX_BODY} bytes` }, { status: 413 });
  return forward("/ask", { method: "POST", body }, TIMEOUT_MS);
}
