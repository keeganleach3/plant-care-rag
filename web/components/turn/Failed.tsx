// An error card per kind, with Retry; the wording lives in lib/errors.tsx.
import { useEffect, useState } from "react";
import { message } from "@/lib/errors";
import type { AskError } from "@/lib/types";
import { ALERT, Icon, RETRY } from "../icons";

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
