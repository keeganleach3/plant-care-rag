import { ASK_TIMEOUT_S } from "@/lib/api";
import { forward, readCapped, refuse } from "@/lib/upstream";

const MAX_BODY = 4096; // bytes, the service's own cap (rag/api.py)

export async function POST(req: Request) {
  const refused = refuse(req);
  if (refused) return refused;
  const body = await readCapped(req, MAX_BODY);
  if (body === null) return Response.json({ detail: `request body over ${MAX_BODY} bytes` }, { status: 413 });
  return forward("/ask", { method: "POST", body }, ASK_TIMEOUT_S * 1000);
}
