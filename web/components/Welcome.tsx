// Welcome (punchlist 2026-09-30 §7.3; comp B-welcome): greeting, four prompts from the pool, the composer, and the
// monstera drawing leaving the frame on the right, clipped inside the page.
import { useState, useSyncExternalStore, type ReactNode } from "react";
import { PROMPTS, type Prompt } from "@/lib/prompts";
import { Icon } from "./icons";

const CHIPS: Record<Prompt["icon"], ReactNode> = {
  drop: <path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" />,
  sprout: (
    <>
      <path d="M7 20h10" />
      <path d="M10 20c5.5-2.5.8-6.4 3-10" />
      <path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z" />
      <path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  bug: (
    <>
      <path d="M9 7.1V6a3 3 0 1 1 6 0v1.1" />
      <path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6" />
      <path d="M12 20v-9M6 13H2M22 13h-4M3 21c0-2.1 1.7-3.9 3.8-4M21 21c0-2.1-1.7-3.9-3.8-4M3 5c0 2 1.6 3.8 3.5 4M21 5c0 2-1.6 3.8-3.5 4" />
    </>
  ),
};

const PAGES = Array.from({ length: PROMPTS.length / 4 }, (_, i) => PROMPTS.slice(i * 4, i * 4 + 4));

// The time of day is the browser's; the server renders a blank line (no hydration mismatch).
const never = () => () => {};
const partOfDay = () => {
  const h = new Date().getHours();
  return h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
};

export function Welcome(props: { onPick(question: string): void; disabled: boolean; composer: ReactNode }) {
  const [page, setPage] = useState(0);
  const part = useSyncExternalStore(never, partOfDay, () => null);
  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {/* The clip box reaches the viewport's right edge past the 128rem ceiling, so the drawing is cut by the page,
          never mid-canvas; the drawing itself stays anchored 7.5rem past the composition's right edge. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 -right-[var(--bleed)] overflow-hidden [--bleed:max(0px,(100vw_-_128rem)/2)]"
      >
        <svg
          viewBox="0 0 620 760"
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.13}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="absolute top-15 right-[calc(var(--bleed)_-_7.5rem)] h-190 w-155 text-accent"
        >
          <path d="M310 740 C 300 600, 300 470, 318 330" />
          <path d="M318 330 C 150 330, 40 230, 60 90 C 200 60, 330 150, 318 330 Z" />
          <path d="M318 330 C 480 320, 590 210, 570 70 C 430 50, 310 140, 318 330 Z" />
          <path d="M318 330 C 250 250, 170 180, 90 120" />
          <path d="M318 330 C 400 240, 480 170, 545 100" />
          <path d="M306 520 C 180 540, 90 500, 60 420 C 150 380, 260 420, 306 520 Z" />
          <path d="M306 520 C 220 480, 150 450, 85 430" />
        </svg>
      </div>
      <div className="relative flex flex-1 flex-col overflow-y-auto px-4 py-6 md:pr-16 md:pl-6">
        <div className="m-auto flex w-full max-w-205 flex-col gap-7">
          <div>
            <h1 className="text-display font-[420]">
              <span className="text-greet">{part ? `Good ${part}, grower.` : "\u00a0"}</span>
              <br />
              What would you like to know?
            </h1>
            <p className="mt-4 max-w-155 text-secondary">
              Answers come only from one grower’s verified notes on Monstera, Alocasia, Anthurium and Philodendron, and
              every answer shows its sources.
            </p>
          </div>
          {/* Every page is laid out in one grid cell and only the current one is visible, so the frame is sized to
              the tallest page and refreshing never moves what sits below it. */}
          <div aria-live="polite" className="grid">
            {PAGES.map((prompts, i) => (
              <div
                key={i}
                className={`col-start-1 row-start-1 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4 ${i === page ? "" : "invisible"}`}
              >
                {prompts.map((p) => (
                  <button
                    key={p.text}
                    type="button"
                    disabled={props.disabled}
                    onClick={() => props.onPick(p.text)}
                    className="flex items-center gap-3 rounded-card bg-card p-4.5 text-left leading-[1.4] shadow-card transition-shadow enabled:hover:shadow-float disabled:cursor-not-allowed sm:min-h-38 sm:flex-col-reverse sm:items-start sm:justify-between sm:gap-4"
                  >
                    <span className="grid size-8.5 shrink-0 place-items-center rounded-chip bg-tint text-accent">
                      <Icon className="size-4.5">{CHIPS[p.icon]}</Icon>
                    </span>
                    <span>{p.text}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setPage((page + 1) % PAGES.length)}
            className="-my-3 flex items-center gap-2 self-start py-3 text-small text-accent hover:text-ink"
          >
            <Icon className="size-4">
              <path d="M3 12a9 9 0 0 1 15.7-6L21 8" />
              <path d="M21 3v5h-5" />
              <path d="M21 12a9 9 0 0 1-15.7 6L3 16" />
              <path d="M8 16H3v5" />
            </Icon>
            Refresh prompts
          </button>
          {props.composer}
        </div>
      </div>
    </div>
  );
}
