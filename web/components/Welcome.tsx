// STUB (architect): W1 builds this — punchlist 2026-09-30 §7.3. Keep the props.
import type { ReactNode } from "react";
import { PROMPTS } from "@/lib/prompts";

export function Welcome(props: { onPick(question: string): void; disabled: boolean; composer: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col justify-center gap-6 overflow-y-auto p-8">
      <h1 className="text-display">What would you like to know?</h1>
      {PROMPTS.slice(0, 4).map((p) => (
        <button key={p.text} disabled={props.disabled} onClick={() => props.onPick(p.text)}>
          {p.text}
        </button>
      ))}
      {props.composer}
    </div>
  );
}
