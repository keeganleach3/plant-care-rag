// Past threads, in this browser only (contract-chat-ui.md §6). Storage can be full, blocked or absent (private
// windows); history is a convenience, so every failure reads as "no history" and never breaks asking.
import type { Thread, Turn } from "./types";

const KEY = "plant-care-rag:threads";
const MAX_THREADS = 50;

// Stored data outlives the code that wrote it: anything that would not render is dropped on load.
const renders = (t: Turn) =>
  typeof t?.question === "string" &&
  !Number.isNaN(Date.parse(t.askedAt)) &&
  t.status === "done" &&
  typeof t.response?.answer === "string" &&
  Array.isArray(t.response.chunks) &&
  Array.isArray(t.response.citations) &&
  Array.isArray(t.response.queries) &&
  typeof t.response.timings?.total_ms === "number";
const valid = (t: Thread) => typeof t?.id === "string" && Array.isArray(t.turns) && t.turns.length > 0 && t.turns.every(renders);

/** Newest first; [] when storage is empty or unavailable. */
export function loadThreads(): Thread[] {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(list) ? list.filter(valid) : [];
  } catch {
    return [];
  }
}

/** Moves the thread to the front, keeping only answered turns; a thread with none is not stored. */
export function saveThread(thread: Thread): void {
  const turns = thread.turns.filter((t) => t.status === "done");
  if (!turns.length) return;
  const list = [{ ...thread, turns }, ...loadThreads().filter((t) => t.id !== thread.id)].slice(0, MAX_THREADS);
  // Storage full: drop the oldest threads until this one fits. Blocked storage empties the list and stores nothing.
  while (list.length) {
    try {
      localStorage.setItem(KEY, JSON.stringify(list));
      return;
    } catch {
      list.pop();
    }
  }
}

export function clearThreads(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // nothing stored to clear
  }
}
