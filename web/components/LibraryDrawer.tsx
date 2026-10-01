// Library (punchlist 2026-09-30 §7.3): everything indexed, as /sources lists it (genus, then title): notes grouped by
// genus, each opening to its sections, each section to its full text.
import { message } from "@/lib/errors";
import type { AskError, Note, Sources, SourcesState } from "@/lib/types";
import { capitalize, plural } from "@/lib/format";
import { Icon } from "./icons";
import { Sheet } from "./Sheet";

const chevron = <path d="m6 9 6 6 6-6" />;
// Insertion order keeps /sources' genus-then-title order.
const byGenus = (notes: Note[]) =>
  notes.reduce<Record<string, Note[]>>((groups, note) => ((groups[note.genus] ??= []).push(note), groups), {});
const summary = "flex cursor-pointer list-none items-center gap-3 rounded-tile px-2 [&::-webkit-details-marker]:hidden";

export function LibraryDrawer(props: {
  open: boolean;
  onClose(): void;
  sources: Sources | null;
  sourcesState: SourcesState;
  sourcesError: AskError | null;
  onReconnect(): void;
}) {
  const notes = props.sources?.notes ?? [];
  const sections = notes.reduce((n, note) => n + note.sections.length, 0);
  return (
    <Sheet
      open={props.open}
      onClose={props.onClose}
      title="Library"
      meta={props.sources && `${plural(notes.length, "note")} · ${plural(sections, "section")}`}
    >
      {props.sourcesState === "offline" ? (
        <p className="px-5 text-secondary">
          {props.sourcesError ? message(props.sourcesError) : "Can’t reach the notes."}{" "}
          <button type="button" onClick={props.onReconnect} className="-my-2 py-2 text-accent hover:text-ink">
            Try again
          </button>
        </p>
      ) : !props.sources ? (
        <p className="px-5 text-secondary">Loading the notes…</p>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
          {Object.entries(byGenus(notes)).map(([genus, group]) => (
            <section key={genus} className="mt-3">
              <h3 className="px-2 py-1 text-small font-[560] text-secondary">
                {capitalize(genus)} · {plural(group.length, "note")}
              </h3>
              {group.map((note) => (
                <details key={note.slug} className="group/note rounded-tile open:bg-pill">
                  <summary className={`${summary} py-2.5 hover:bg-pill`}>
                    <span className="min-w-0 flex-1 font-[560]">{note.title}</span>
                    <span className="shrink-0 text-small text-secondary">{plural(note.sections.length, "section")}</span>
                    <Icon className="size-4 shrink-0 text-secondary group-open/note:rotate-180">{chevron}</Icon>
                  </summary>
                  <div className="px-2 pb-2">
                    {note.sections.map((s) => (
                      <details key={s.chunk_id} className="group/section">
                        <summary className={`${summary} py-2 hover:bg-card`}>
                          <span className="min-w-0 flex-1">{s.heading}</span>
                          <Icon className="size-4 shrink-0 text-secondary group-open/section:rotate-180">{chevron}</Icon>
                        </summary>
                        <p className="px-2 pt-1 pb-3 text-small whitespace-pre-line text-secondary">{s.content}</p>
                      </details>
                    ))}
                  </div>
                </details>
              ))}
            </section>
          ))}
        </div>
      )}
    </Sheet>
  );
}
