// Punchlist 2026-09-30 §7.4, from the B-answer comp. The props are the contract with Chat.tsx.
import { useEffect, useRef } from "react";
import type { Turn as TurnData } from "@/lib/types";
import { Turn } from "./Turn";

export function Thread(props: {
  turns: TurnData[];
  activeId: string | null;
  onActivate(id: string): void;
  onRetry(id: string): void;
  busy: boolean;
  titles: Map<string, string>;
  inlineSources: boolean;
}) {
  const { turns, activeId, onActivate, onRetry, busy, titles, inlineSources } = props;
  const list = useRef<HTMLDivElement>(null);
  const shown = useRef<string | undefined>(undefined);
  const lastId = turns.at(-1)?.id;
  const lastStatus = turns.at(-1)?.status;

  // The last turn scrolls into view, its question at the top of the region. A new question, or this one settling,
  // glides there (instant under reduced motion); opening a thread jumps.
  useEffect(() => {
    const glide =
      (lastStatus === "pending" || shown.current === lastId) &&
      !matchMedia("(prefers-reduced-motion: reduce)").matches;
    shown.current = lastId;
    list.current?.lastElementChild?.scrollIntoView({ behavior: glide ? "smooth" : "instant", block: "start" });
  }, [lastId, lastStatus]);

  // The aside follows one answer; with several, a ring marks which.
  const ring = !inlineSources && turns.length > 1;

  return (
    <section aria-label="Conversation" className="flex min-h-0 flex-1 flex-col">
      <header className="flex h-14 shrink-0 items-center px-4 md:h-[4.5rem] md:px-12">
        <h1 className="truncate text-small text-secondary">{turns[0]?.question}</h1>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div ref={list} className="mx-auto flex max-w-[53.75rem] flex-col gap-10 px-4 pt-0.5 pb-8 md:px-9">
          {turns.map((t) => (
            <Turn
              key={t.id}
              turn={t}
              ring={ring && t.id === activeId}
              onActivate={inlineSources ? undefined : () => onActivate(t.id)}
              onRetry={() => onRetry(t.id)}
              busy={busy}
              titles={titles}
              inlineSources={inlineSources}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
