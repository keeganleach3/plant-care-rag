// STUB (architect): W1 builds this — punchlist 2026-09-30 §7.3. Keep the props.
import type { Sources, SourcesState } from "@/lib/types";

export function LibraryDrawer(props: {
  open: boolean;
  onClose(): void;
  sources: Sources | null;
  sourcesState: SourcesState;
  onReconnect(): void;
}) {
  if (!props.open) return null;
  return (
    <div role="dialog" aria-label="Library">
      <button onClick={props.onClose}>Close</button>
      {props.sources?.notes.map((n) => <p key={n.slug}>{n.title}</p>)}
    </div>
  );
}
