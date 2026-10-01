// Rail (punchlist 2026-09-30 §7.3; contract-chat-ui.md §6): logo and New chat start a new chat; History and Library
// open their drawers. A top bar below 768px.
import type { Drawer } from "@/lib/types";
import { BOOK, Icon } from "./icons";

const round = "grid size-11.5 place-items-center rounded-full";
const quiet = `${round} text-secondary hover:bg-card hover:text-ink aria-expanded:bg-card aria-expanded:text-ink`;

export function Rail(props: { drawer: Drawer; onNewChat(): void; onOpen(drawer: "history" | "library"): void }) {
  return (
    <nav aria-label="Main" className="flex shrink-0 items-center gap-2.5 px-4 py-2 md:w-22 md:flex-col md:px-0 md:py-6">
      <button
        type="button"
        aria-label="Plant Care home, new chat"
        onClick={props.onNewChat}
        className="mr-auto grid size-12 place-items-center rounded-tile bg-brand text-on-answer md:mr-0 md:mb-4"
      >
        <Icon className="size-6">
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </Icon>
      </button>
      <button type="button" aria-label="New chat" onClick={props.onNewChat} className={`${round} bg-card text-ink shadow-raise`}>
        <Icon>
          <path d="M12 5v14M5 12h14" />
        </Icon>
      </button>
      <button
        type="button"
        aria-label="History"
        aria-haspopup="dialog"
        aria-expanded={props.drawer === "history"}
        onClick={() => props.onOpen("history")}
        className={quiet}
      >
        <Icon>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </Icon>
      </button>
      <button
        type="button"
        aria-label="Library"
        aria-haspopup="dialog"
        aria-expanded={props.drawer === "library"}
        onClick={() => props.onOpen("library")}
        className={quiet}
      >
        <Icon d={BOOK} />
      </button>
    </nav>
  );
}
