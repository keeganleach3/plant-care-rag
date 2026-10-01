// Loading (contract-chat-ui.md §6): an answer-shaped placeholder with elapsed seconds. No invented stages.
import { useEffect, useState } from "react";
import { Icon, LEAF } from "../icons";

const since = (iso: string) => Math.max(0, Math.floor((Date.now() - Date.parse(iso)) / 1000));

export function Waiting({ askedAt }: { askedAt: string }) {
  const [seconds, setSeconds] = useState(() => since(askedAt));
  useEffect(() => {
    const tick = setInterval(() => setSeconds(since(askedAt)), 1000);
    return () => clearInterval(tick);
  }, [askedAt]);
  return (
    <div className="rounded-card bg-card px-5 pt-5 pb-6 shadow-card sm:px-7 sm:pt-6 sm:pb-7">
      <p aria-hidden className="mb-4 flex items-center gap-2 text-small leading-tight text-secondary">
        <Icon d={LEAF} className="size-4" />
        Waiting for the answer
        <span className="ml-auto tabular-nums">{seconds} s</span>
      </p>
      {/* Two paragraphs of lines at the answer's line pitch, so the card is near the answer's size. */}
      <div aria-hidden className="flex flex-col gap-[0.95rem] motion-safe:animate-pulse">
        {["w-full", "w-full", "w-2/3", "mt-3 w-full", "w-11/12", "w-1/2"].map((w, i) => (
          <span key={i} className={`h-3 rounded-full bg-sunken ${w}`} />
        ))}
      </div>
      {/* Empty for the first second, so the region exists before it speaks: announced once, never per tick. */}
      <p aria-live="polite" className="sr-only">
        {seconds ? "Waiting for the answer." : ""}
      </p>
    </div>
  );
}
