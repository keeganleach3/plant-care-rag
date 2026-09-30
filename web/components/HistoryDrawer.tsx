// History (punchlist 2026-09-30 §7.3; contract-chat-ui.md §6), and the drawer sheet LibraryDrawer shares.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { Thread } from "@/lib/types";
import { Icon } from "./Rail";

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

/** A native modal dialog: Esc, the backdrop and the close button close it; the browser returns focus to the opener. */
export function Sheet(props: { open: boolean; onClose(): void; title: string; meta?: ReactNode; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const pressedOutside = useRef(false);
  const title = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (props.open && !dialog?.open) dialog?.showModal();
    if (!props.open && dialog?.open) dialog.close();
  }, [props.open]);

  // The dialog box is a transparent frame the size of the composition; a click that both starts and ends on it (or on
  // ::backdrop) closes, so a text selection dragged out of the sheet does not.
  return (
    <dialog
      ref={ref}
      aria-labelledby={title}
      onClose={props.onClose}
      onPointerDown={(e) => {
        pressedOutside.current = e.target === e.currentTarget;
      }}
      onClick={(e) => {
        if (pressedOutside.current && e.target === e.currentTarget) e.currentTarget.close();
      }}
      className="mx-auto my-0 h-dvh max-h-none w-full max-w-[128rem] bg-transparent p-2 text-ink backdrop:bg-ink/30 md:p-3 md:pl-22"
    >
      {props.open && (
        <div className="flex h-full flex-col rounded-card bg-card shadow-float transition-[translate,opacity] duration-200 ease-out starting:-translate-x-4 starting:opacity-0 md:w-120">
          <header className="flex shrink-0 items-start gap-3 py-3 pr-3 pl-5">
            <div className="min-w-0 flex-1 pt-2.5">
              <h2 id={title} className="font-[560]">
                {props.title}
              </h2>
              {props.meta && <p className="text-small text-secondary">{props.meta}</p>}
            </div>
            <button
              type="button"
              aria-label="Close"
              onClick={() => ref.current?.close()}
              className="grid size-11 shrink-0 place-items-center rounded-full text-secondary hover:bg-pill hover:text-ink"
            >
              <Icon>
                <path d="M18 6 6 18M6 6l12 12" />
              </Icon>
            </button>
          </header>
          {props.children}
        </div>
      )}
    </dialog>
  );
}

const when = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

export function HistoryDrawer(props: {
  open: boolean;
  onClose(): void;
  threads: Thread[];
  onOpenThread(thread: Thread): void;
  onClear(): void;
}) {
  const [query, setQuery] = useState("");
  const [confirming, setConfirming] = useState(false);
  const filter = useRef<HTMLInputElement>(null);
  const q = query.trim().toLowerCase();
  const shown = props.threads.filter((t) => t.turns.some((turn) => turn.question.toLowerCase().includes(q)));
  const n = props.threads.length;

  const clear = () => {
    props.onClear();
    setConfirming(false);
    filter.current?.focus(); // the pressed button is gone; keep focus in the sheet
  };

  return (
    <Sheet
      open={props.open}
      onClose={() => {
        setQuery("");
        setConfirming(false);
        props.onClose();
      }}
      title="History"
      meta="Saved in this browser only"
    >
      <input
        ref={filter}
        type="search"
        aria-label="Filter conversations"
        placeholder="Filter by question"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="mx-5 h-11 shrink-0 rounded-full bg-pill px-4 placeholder:text-quiet"
      />
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {shown.length ? (
          <ul>
            {shown.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => props.onOpenThread(t)}
                  className="w-full rounded-tile px-3 py-2.5 text-left hover:bg-pill"
                >
                  <span className="line-clamp-2">{t.turns[0]?.question}</span>
                  <span className="block text-small text-secondary">
                    {plural(t.turns.length, "question")} · {when.format(new Date(t.turns.at(-1)?.askedAt ?? t.createdAt))}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-3 py-2 text-secondary">
            {n ? `No conversations match “${query.trim()}”.` : "No saved conversations yet. Answered questions are kept here."}
          </p>
        )}
      </div>
      {/* Clearing is never one click: the first press asks, and turns itself into Cancel. */}
      {n > 0 && (
        <footer className="flex shrink-0 flex-wrap items-center justify-end gap-2 px-5 pt-2 pb-4 text-small">
          {confirming && <span className="mr-auto">Clear {plural(n, "saved conversation")}?</span>}
          {confirming && (
            <button type="button" onClick={clear} className="h-11 rounded-full bg-ink px-4 font-[560] text-on-answer">
              Clear all
            </button>
          )}
          <button
            type="button"
            onClick={() => setConfirming(!confirming)}
            className="h-11 rounded-full px-4 text-secondary hover:bg-pill hover:text-ink"
          >
            {confirming ? "Cancel" : "Clear all"}
          </button>
        </footer>
      )}
    </Sheet>
  );
}
