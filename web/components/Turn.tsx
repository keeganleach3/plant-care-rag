// One question and what came back: the answer (or refusal), a placeholder while waiting, or the error with Retry.
import type { Turn as TurnData } from "@/lib/types";
import { AnswerCard } from "./AnswerCard";
import { SourcesPanel } from "./SourcesPanel";
import { Failed } from "./turn/Failed";
import { Icon, SPLIT } from "./turn/icons";
import { Waiting } from "./turn/Waiting";

export function Turn({
  turn,
  ring,
  onActivate,
  onRetry,
  busy,
  titles,
  inlineSources,
}: {
  turn: TurnData;
  ring: boolean;
  onActivate?: () => void; // absent when the sources sit inline: nothing to switch
  onRetry(): void;
  busy: boolean;
  titles: Map<string, string>;
  inlineSources: boolean;
}) {
  const r = turn.status === "done" ? turn.response : undefined;
  return (
    <article className="flex scroll-mt-2 flex-col gap-[1.125rem]">
      <p className="ml-10 max-w-[37.25rem] self-end rounded-card rounded-br-[0.375rem] bg-card px-[1.125rem] py-3.5 leading-normal break-words whitespace-pre-line shadow-card">
        {turn.question}
      </p>
      {r && r.queries.length > 1 && (
        <ul className="flex flex-wrap items-center gap-2 text-small leading-tight text-secondary">
          <li className="mr-1 flex items-center gap-1.5">
            <Icon d={SPLIT} />
            Searched {r.queries.length} ways
          </li>
          {r.queries.map((q, i) => (
            <li key={i} className="rounded-full bg-card px-3 py-1.5 break-words text-sunken-ink ring-1 ring-ink/6">
              {i ? q : "the whole message"}
            </li>
          ))}
        </ul>
      )}
      {turn.status === "pending" && <Waiting askedAt={turn.askedAt} />}
      {turn.status === "error" && turn.error && <Failed error={turn.error} onRetry={onRetry} busy={busy} />}
      {r && <AnswerCard response={r} ring={ring} onActivate={onActivate} />}
      {r && inlineSources && <SourcesPanel turn={turn} titles={titles} />}
    </article>
  );
}
