// Composer (punchlist 2026-09-30 §7.3): the welcome card (comp B-welcome) and the docked pill (comp B-answer).
// Enter asks, Shift+Enter is a new line; Ask is disabled when empty, over the limit, offline or pending.
import { useId, type FormEvent } from "react";
import { MAX_QUESTION } from "@/lib/api";
import { GENERA, type Genus, type SourcesState } from "@/lib/types";
import { BOOK, Icon } from "./Rail";

const name = (g: string) => g[0].toUpperCase() + g.slice(1);

// The comp draws no ring on the textarea; the card (or pill) around it carries the focus ring instead.
const ring =
  "has-[textarea:focus-visible]:outline-2 has-[textarea:focus-visible]:outline-offset-2 has-[textarea:focus-visible]:outline-accent";

export function Composer(props: {
  variant: "welcome" | "docked";
  value: string;
  onChange(value: string): void;
  onSubmit(): void;
  genus: Genus | null;
  onGenus(genus: Genus | null): void;
  pending: boolean;
  sourcesState: SourcesState;
  corpus: { notes: number; sections: number } | null;
  onReconnect(): void;
}) {
  const counter = useId();
  const n = props.value.trim().length;
  const over = n > MAX_QUESTION;
  const offline = props.sourcesState === "offline";
  const canAsk = n > 0 && !over && !props.pending && !offline;
  const docked = props.variant === "docked";
  const showCount = !docked || over; // the docked pill shows the count only once it is over

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (canAsk) props.onSubmit();
  };

  const textarea = (
    <textarea
      aria-label="Your question"
      aria-describedby={showCount ? counter : undefined}
      rows={docked ? 1 : 2}
      value={props.value}
      placeholder={docked ? "Ask another question…" : "Ask about your aroids…"}
      onChange={(e) => props.onChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing) return;
        e.preventDefault();
        if (canAsk) props.onSubmit();
      }}
      className={`min-w-0 flex-1 resize-none bg-transparent py-0.5 leading-normal outline-none! placeholder:text-quiet ${docked ? "basis-full max-sm:px-3.5 sm:basis-0" : ""}`}
    />
  );

  // A genus keeps the general notes in scope (that is how the search filter works); the option group says so.
  const genus = (
    <span className="relative shrink-0">
      <select
        aria-label="Genus"
        value={props.genus ?? ""}
        onChange={(e) => props.onGenus((e.target.value || null) as Genus | null)}
        className="field-sizing-content appearance-none rounded-full bg-pill py-2 pr-8.5 pl-3 text-small text-sunken-ink"
      >
        <option value="">All genera</option>
        <optgroup label="One genus, plus the general notes">
          {GENERA.map((g) => (
            <option key={g} value={g}>
              {name(g)}
            </option>
          ))}
        </optgroup>
      </select>
      <Icon className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-sunken-ink">
        <path d="m6 9 6 6 6-6" />
      </Icon>
    </span>
  );

  const ask = (
    <button
      type="submit"
      disabled={!canAsk}
      className="ml-auto flex h-10.5 shrink-0 items-center gap-2 rounded-full bg-ink px-4.5 text-small font-[560] text-on-answer disabled:bg-pill disabled:text-quiet"
    >
      Ask
      <Icon className="size-4">
        <path d="m5 12 7-7 7 7M12 19V5" />
      </Icon>
    </button>
  );

  const count = (
    <span id={counter} className={`text-small tabular-nums ${over ? "font-[560] text-ink" : "text-quiet"}`}>
      {n}/{MAX_QUESTION}
    </span>
  );

  const reconnect = (
    <span className="flex items-center gap-1.5">
      Can’t reach the notes.
      <button type="button" onClick={props.onReconnect} className="-my-2 py-2 text-accent hover:text-ink">
        Try again
      </button>
    </span>
  );

  if (docked)
    return (
      <div className="mx-auto w-full max-w-215 px-4 pt-3 pb-4 md:px-9 md:pt-3.5 md:pb-6">
        {offline && <p className="mb-2 px-2 text-small text-secondary">{reconnect}</p>}
        <form
          onSubmit={onSubmit}
          className={`flex flex-wrap items-center gap-x-3 gap-y-2 rounded-card bg-card p-2 shadow-float sm:flex-nowrap sm:rounded-full sm:pl-5.5 ${ring}`}
        >
          {textarea}
          {showCount && count}
          {genus}
          {ask}
        </form>
      </div>
    );

  return (
    <form onSubmit={onSubmit} className={`rounded-card bg-card px-5 pt-5 pb-4 shadow-float ${ring}`}>
      <div className="flex items-start gap-3">
        {textarea}
        {genus}
      </div>
      <div className="mt-4.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-4.5 gap-y-1 text-small text-secondary">
          <span className="flex items-center gap-1.5">
            <Icon className="size-4">
              <path d="M16 3h5v5M8 3H3v5M12 22v-8.3a4 4 0 0 0-1.2-2.9L3 3M15 9l6-6" />
            </Icon>
            Splits multi-part questions
          </span>
          {offline
            ? reconnect
            : props.corpus && (
                <span className="flex items-center gap-1.5 tabular-nums">
                  <Icon className="size-4">{BOOK}</Icon>
                  {props.corpus.notes} notes · {props.corpus.sections} sections
                </span>
              )}
        </div>
        <div className="ml-auto flex items-center gap-3.5">
          {count}
          {ask}
        </div>
      </div>
    </form>
  );
}
