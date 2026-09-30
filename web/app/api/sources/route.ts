import { forward } from "@/lib/upstream";

export async function GET() {
  return forward("/sources", { method: "GET" }, 10_000);
}
