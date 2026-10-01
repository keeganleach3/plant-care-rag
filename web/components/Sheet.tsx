// The drawer sheet History and Library share (contract-chat-ui.md §6).
import { useEffect, useId, useRef, type ReactNode } from "react";
import { CLOSE, Icon } from "./icons";

/** A native modal dialog: Esc, the backdrop and the close button close it; the browser returns focus to the opener. */
export function Sheet(props: { open: boolean; onClose(): void; title: string; meta?: ReactNode; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const pressedOutside = useRef(false);
  const title = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (props.open && !dialog?.open) dialog?.showModal();
    if (!props.open && dialog?.open) dialog.close();
  }, [props.open]);

  // The dialog box is a transparent frame the size of the composition; a click that both starts and ends on it (or on
  // ::backdrop) closes, so a text selection dragged out of the sheet does not.
  return (
    <dialog
      ref={ref}
      aria-labelledby={title}
      onClose={props.onClose}
      onPointerDown={(e) => {
        pressedOutside.current = e.target === e.currentTarget;
      }}
      onClick={(e) => {
        if (pressedOutside.current && e.target === e.currentTarget) e.currentTarget.close();
      }}
      className="mx-auto my-0 h-dvh max-h-none w-full max-w-[128rem] bg-transparent p-2 text-ink backdrop:bg-ink/30 md:p-3 md:pl-22"
    >
      {props.open && (
        <div className="flex h-full flex-col rounded-card bg-card shadow-float transition-[translate,opacity] duration-200 ease-out starting:-translate-x-4 starting:opacity-0 md:w-120">
          <header className="flex shrink-0 items-start gap-3 py-3 pr-3 pl-5">
            <div className="min-w-0 flex-1 pt-2.5">
              <h2 id={title} className="font-[560]">
                {props.title}
              </h2>
              {props.meta && <p className="text-small text-secondary">{props.meta}</p>}
            </div>
            <button
              type="button"
              aria-label="Close"
              onClick={() => ref.current?.close()}
              className="grid size-11 shrink-0 place-items-center rounded-full text-secondary hover:bg-pill hover:text-ink"
            >
              <Icon d={CLOSE} />
            </button>
          </header>
          {props.children}
        </div>
      )}
    </dialog>
  );
}
