import { forward, refuse } from "@/lib/upstream";

export async function GET(req: Request) {
  return refuse(req) ?? forward("/sources", { method: "GET" }, 10_000);
}
