// One retrieved section: a white card when cited, a sunken tile when not used. Opens to the full section text.
import type { Chunk } from "@/lib/types";
import { CHECK, Icon } from "./turn/icons";

export function SourceCard({ chunk, note, cited }: { chunk: Chunk; note: string; cited: boolean }) {
  const meta = cited ? "text-secondary" : "text-sunken-meta";
  return (
    <details className={`group ${cited ? "rounded-card bg-card shadow-card" : "rounded-tile bg-sunken"}`}>
      <summary
        className={`flex cursor-pointer list-none flex-col rounded-[inherit] px-[1.125rem] leading-tight [&::-webkit-details-marker]:hidden ${cited ? "gap-1.5 py-4 group-open:pb-1.5" : "gap-1 py-3.5 group-open:pb-1"}`}
      >
        <span className={`flex items-center justify-between gap-3 text-small leading-tight ${meta}`}>
          <span className="min-w-0 truncate group-open:whitespace-normal">{note}</span>
          {cited ? (
            <span className="flex shrink-0 items-center gap-1 rounded-full bg-tint px-2.5 py-[0.1875rem] text-brand">
              <Icon d={CHECK} stroke={2.4} className="size-3.5" />
              Cited
            </span>
          ) : (
            <span className="shrink-0">Not used</span>
          )}
        </span>
        <span className={cited ? "font-[560]" : "text-sunken-ink"}>{chunk.heading}</span>
        {/* A preview of the text below; screen readers get the full text when the card opens. */}
        {cited && (
          <span aria-hidden className={`line-clamp-3 text-small ${meta} group-open:hidden`}>
            {chunk.content}
          </span>
        )}
      </summary>
      <p className={`px-[1.125rem] text-small ${meta} ${cited ? "pb-4" : "pb-3.5"}`}>{chunk.content}</p>
    </details>
  );
}
