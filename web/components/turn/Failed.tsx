// An error card per kind, with Retry. Wording: punchlist 2026-09-30 §7.4 (`kind`, then `detail` for 502s).
import { useEffect, useState, type ReactNode } from "react";
import type { AskError } from "@/lib/types";
import { ALERT, Icon, RETRY } from "../icons";

const GENERATION = new Map([
  ["timeout", "The model took too long to answer."],
  ["cli_error", "The model call failed."],
  ["schema_invalid", "The model's reply came back malformed, so it was withheld."],
  ["citation_invalid", "The answer cited a section it wasn't given, so it was withheld."],
  ["model_mismatch", "A different model answered than the one configured, so the answer was withheld."],
  ["refusal", "The model declined to answer."],
]);

function message({ kind, detail, status }: AskError): ReactNode {
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
      return "No answer after 150 seconds, so the app stopped waiting.";
    case "generation":
      return GENERATION.get(detail) ?? `Generation failed${detail ? ` (${detail})` : ""}.`;
    case "rejected":
      return "The service rejected this app's key. Check RAG_API_KEY in web/.env.local.";
    default:
      return `Something went wrong (${status}).`;
  }
}

export function Failed({ error, onRetry, busy }: { error: AskError; onRetry(): void; busy: boolean }) {
  // busy only: count down the service's Retry-After, then drop the hint.
  const [wait, setWait] = useState(error.kind === "busy" ? (error.retryAfter ?? 0) : 0);
  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait(wait - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);
  return (
    <div className="flex flex-col gap-3 rounded-card bg-card px-5 py-5 shadow-card sm:flex-row sm:gap-4 sm:px-7 sm:py-6">
      <span className="grid size-[2.125rem] shrink-0 place-items-center rounded-chip bg-tint text-accent">
        <Icon d={ALERT} className="size-[1.125rem]" />
      </span>
      <div className="flex min-w-0 flex-col items-start gap-4 sm:pt-1">
        <p role="alert" className="break-words">
          {message(error)}
        </p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <button
            type="button"
            onClick={onRetry}
            disabled={busy}
            className="flex h-[2.625rem] items-center gap-2 rounded-full bg-ink px-[1.125rem] text-small font-[560] text-on-answer enabled:cursor-pointer disabled:opacity-50"
          >
            Retry
            <Icon d={RETRY} stroke={2.2} className="size-4" />
          </button>
          {wait > 0 && <span className="text-small text-secondary tabular-nums">Try again in {wait} s</span>}
        </div>
      </div>
    </div>
  );
}
