// Punchlist 2026-09-30 §7.4. The props are the contract with Chat.tsx: it renders this in the aside at ≥1280px,
// and Turn renders it inline under each answer below that, so the aside's padding is xl-only (xl = 80rem = 1280px).
import type { Turn } from "@/lib/types";
import { SourceCard } from "./SourceCard";

export function SourcesPanel({ turn, titles }: { turn: Turn | null; titles: Map<string, string> }) {
  const r = turn?.status === "done" ? turn.response : undefined;
  const cited = r ? [...new Set(r.citations)].flatMap((id) => r.chunks.filter((c) => c.chunk_id === id)) : [];
  const unused = r ? r.chunks.filter((c) => !r.citations.includes(c.chunk_id)) : [];
  const note = (chunkId: string) => {
    const slug = chunkId.split("#")[0];
    return titles.get(slug) ?? slug;
  };
  return (
    // Keyed by turn: following another answer starts with every card closed.
    <div key={turn?.id} className="flex flex-col gap-3 xl:pt-[1.375rem] xl:pr-6 xl:pb-[1.375rem] xl:pl-2">
      <div className="flex items-baseline justify-between gap-3 px-1 pt-1.5 pb-0.5 leading-tight">
        <h2 className="font-[560]">{r?.refused ? "Closest sections searched" : "Sources"}</h2>
        {r && (
          <p className="text-small text-secondary">
            {r.refused ? `${unused.length} not used` : `${cited.length} cited · ${unused.length} not used`}
          </p>
        )}
      </div>
      {!r && <p className="px-1 text-small text-secondary">The sections it searched show here with the answer.</p>}
      {cited.map((c) => (
        <SourceCard key={c.chunk_id} chunk={c} note={note(c.chunk_id)} cited />
      ))}
      {unused.map((c) => (
        <SourceCard key={c.chunk_id} chunk={c} note={note(c.chunk_id)} cited={false} />
      ))}
    </div>
  );
}
