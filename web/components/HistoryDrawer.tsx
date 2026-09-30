// STUB (architect): W1 builds this — punchlist 2026-09-30 §7.3. Keep the props.
import type { Thread } from "@/lib/types";

export function HistoryDrawer(props: {
  open: boolean;
  onClose(): void;
  threads: Thread[];
  onOpenThread(thread: Thread): void;
  onClear(): void;
}) {
  if (!props.open) return null;
  return (
    <div role="dialog" aria-label="History">
      <button onClick={props.onClose}>Close</button>
      {props.threads.map((t) => (
        <button key={t.id} onClick={() => props.onOpenThread(t)}>
          {t.turns[0]?.question}
        </button>
      ))}
    </div>
  );
}
