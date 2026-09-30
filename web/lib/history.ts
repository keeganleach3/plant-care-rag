// Past threads, in this browser only (contract-chat-ui.md §6). Storage can be full, blocked or absent (private
// windows); history is a convenience, so every failure reads as "no history" and never breaks asking.
import type { Thread } from "./types";

const KEY = "plant-care-rag:threads";
const MAX_THREADS = 50;

/** Newest first; [] when storage is empty or unavailable. */
export function loadThreads(): Thread[] {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

/** Moves the thread to the front, keeping only answered turns; a thread with none is not stored. */
export function saveThread(thread: Thread): void {
  const turns = thread.turns.filter((t) => t.status === "done");
  if (!turns.length) return;
  const list = [{ ...thread, turns }, ...loadThreads().filter((t) => t.id !== thread.id)].slice(0, MAX_THREADS);
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // quota or blocked storage: this thread just isn't kept
  }
}

export function clearThreads(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // nothing stored to clear
  }
}
