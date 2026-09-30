// STUB (architect): W1 builds this — punchlist 2026-09-30 §7.3. Keep the props.
import type { Drawer } from "@/lib/types";

export function Rail(props: { drawer: Drawer; onNewChat(): void; onOpen(drawer: "history" | "library"): void }) {
  return (
    <nav aria-label="Main" className="flex gap-2 p-4 md:flex-col">
      <button onClick={props.onNewChat}>New chat</button>
      <button onClick={() => props.onOpen("history")}>History</button>
      <button onClick={() => props.onOpen("library")}>Library</button>
    </nav>
  );
}
