// What went wrong, in plain words: punchlist 2026-09-30 §7.4 (`kind`, then `detail` for 502s). Used by the error card,
// and by the composer and the library when /sources fails at load.
import type { ReactNode } from "react";
import { ASK_TIMEOUT_S } from "./api";
import type { AskError } from "./types";

const GENERATION = new Map([
  ["timeout", "The model took too long to answer."],
  ["cli_error", "The model call failed."],
  ["schema_invalid", "The model's reply came back malformed, so it was withheld."],
  ["citation_invalid", "The answer cited a section it wasn't given, so it was withheld."],
  ["model_mismatch", "A different model answered than the one configured, so the answer was withheld."],
  ["refusal", "The model declined to answer."],
]);

export function message({ kind, detail, status }: AskError): ReactNode {
  switch (kind) {
    case "busy":
      return "The service is answering other questions right now.";
    case "db":
      return "The notes database isn't reachable. Is Docker running?";
    case "embed_model":
      return "The index was built with a different embedding model. Re-ingest the notes, then try again.";
    case "unreachable":
      return detail === "web server" ? (
        "Can't reach this app's server."
      ) : (
        <>
          Can&apos;t reach the answer service. Start it from the project folder with <code>uv run uvicorn rag.api:app</code>.
        </>
      );
    case "timeout":
      return `No answer after ${ASK_TIMEOUT_S} seconds, so the app stopped waiting. The service may still finish it.`;
    case "generation":
      return GENERATION.get(detail) ?? `Generation failed${detail ? ` (${detail})` : ""}.`;
    case "rejected":
      return "The service rejected this app's key. Check RAG_API_KEY in web/.env.local.";
    default:
      return `Something went wrong (${status}).`;
  }
}
