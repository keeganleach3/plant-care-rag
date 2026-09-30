// STUB (architect): W1 builds this — punchlist 2026-09-30 §7.3. Keep the props.
import type { Genus, SourcesState } from "@/lib/types";

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
  return (
    <form
      className="flex gap-2 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        props.onSubmit();
      }}
    >
      <label htmlFor="question" className="sr-only">
        Your question
      </label>
      <textarea id="question" value={props.value} onChange={(e) => props.onChange(e.target.value)} />
      <button type="submit" disabled={props.pending}>
        Ask
      </button>
    </form>
  );
}
