// STUB (architect): W2 builds this — punchlist 2026-09-30 §7.4. Keep the props.
import type { Turn } from "@/lib/types";

export function SourcesPanel(props: { turn: Turn | null; titles: Map<string, string> }) {
  return (
    <div className="p-6">
      <h2>Sources</h2>
      {props.turn?.response?.chunks.map((c) => <p key={c.chunk_id}>{c.heading}</p>)}
    </div>
  );
}
