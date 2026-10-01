// Lucide paths as the B comps draw them: 24-unit grid, stroke 2, round caps and joins. Sized by the caller's class (rem),
// so they scale with the root. Decorative: the control that holds one carries the label.
import type { ReactNode } from "react";

export const LEAF =
  "M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10ZM2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12";
export const BOOK = "M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2zM22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z";
export const SPLIT = "M16 3h5v5M8 3H3v5M12 22v-8.3a4 4 0 0 0-1.2-2.9L3 3M15 9l6-6";
export const CHECK = "M20 6 9 17l-5-5";
export const CLOSE = "M18 6 6 18M6 6l12 12";
export const ALERT = "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM12 8v4M12 16h.01";
export const RETRY = "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8M3 3v5h5";

/** One path from `d`, or several shapes as children. */
export function Icon(props: { d?: string; className?: string; stroke?: number; children?: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={props.stroke ?? 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={`shrink-0 ${props.className ?? "size-5"}`}
    >
      {props.d ? <path d={props.d} /> : props.children}
    </svg>
  );
}
