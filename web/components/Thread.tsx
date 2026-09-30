// STUB (architect): W2 builds this — punchlist 2026-09-30 §7.4. Keep the props.
import type { Turn } from "@/lib/types";

export function Thread(props: {
  turns: Turn[];
  activeId: string | null;
  onActivate(id: string): void;
  onRetry(id: string): void;
  busy: boolean;
  titles: Map<string, string>;
  inlineSources: boolean;
}) {
  return (
    <section aria-label="Conversation" className="flex-1 overflow-y-auto p-8">
      {props.turns.map((t) => (
        <article key={t.id}>
          <p>{t.question}</p>
          <p>{t.status === "done" ? t.response?.answer : t.status}</p>
        </article>
      ))}
    </section>
  );
}
