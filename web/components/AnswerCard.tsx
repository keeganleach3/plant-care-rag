// The answer in the forest block (the AI's own voice); a refusal gets a white card (contract-chat-ui.md §6).
import type { AskResponse } from "@/lib/types";
import { Icon, LEAF } from "./icons";

type Part = { list?: "ul" | "ol"; start?: number; lines: string[] };

// Lines starting "- " or "1. " become list items and join the list above them even across a blank line, so
// "1. a\n\n2. b" stays one list. Other lines join the paragraph directly above; a blank line starts a new one.
// Text nodes only.
function parts(text: string): Part[] {
  const out: Part[] = [];
  let gap = true;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) {
      gap = true;
      continue;
    }
    const item = /^(?:-|(\d+)\.)\s+(.*)$/.exec(line);
    const list = item ? (item[1] ? "ol" : "ul") : undefined;
    const content = item ? item[2] : line;
    const last = out.at(-1);
    if (last && last.list === list && (list || !gap)) last.lines.push(content);
    else out.push({ list, start: item?.[1] ? Number(item[1]) : undefined, lines: [content] });
    gap = false;
  }
  return out;
}

export function AnswerCard({
  response,
  ring,
  onActivate,
}: {
  response: AskResponse;
  ring?: boolean;
  onActivate?: () => void;
}) {
  const { refused, citations, chunks, timings } = response;
  // The solid colour under the gradient keeps the light text readable wherever gradients don't paint.
  const skin = refused
    ? "bg-card shadow-card"
    : "bg-answer-to bg-linear-160 from-answer-from to-answer-to text-on-answer shadow-answer";
  const meta = refused ? "text-secondary" : "text-on-answer-meta";
  const cited = `Cited ${new Set(citations).size} of ${chunks.length} retrieved sections`;
  return (
    <div
      className={`rounded-card px-5 pt-5 pb-4 sm:px-7 sm:pt-6 sm:pb-5 ${skin} ${ring ? "outline-2 outline-offset-4 outline-accent" : ""}`}
    >
      <p className={`mb-2.5 flex items-center gap-2 text-small leading-tight ${meta}`}>
        <Icon d={LEAF} className="size-4" />
        {refused ? "Not in the grower’s notes" : "From the grower’s notes"}
      </p>
      <div className="flex flex-col gap-3 leading-[1.62] break-words">
        {parts(response.answer).map(({ list: List, start, lines }, i) =>
          List ? (
            <List key={i} start={start} className={`pl-5 ${List === "ul" ? "list-disc" : "list-decimal"}`}>
              {lines.map((line, j) => (
                <li key={j}>{line}</li>
              ))}
            </List>
          ) : (
            <p key={i}>{lines.join(" ")}</p>
          ),
        )}
      </div>
      <div
        className={`mt-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-small leading-tight tabular-nums ${meta}`}
      >
        {onActivate ? (
          // Makes this answer the one the Sources aside follows. On the forest block the focus ring is light.
          <button
            type="button"
            onClick={onActivate}
            aria-pressed={ring}
            className={`min-h-6 cursor-pointer rounded-chip underline-offset-4 hover:underline ${refused ? "" : "focus-visible:outline-on-answer"}`}
          >
            {cited}
          </button>
        ) : (
          <span>{cited}</span>
        )}
        <span>
          Answered in {(timings.total_ms / 1000).toFixed(1)} s · retrieval{" "}
          {Math.round(timings.embed_ms + timings.retrieve_ms)} ms
        </span>
      </div>
    </div>
  );
}
