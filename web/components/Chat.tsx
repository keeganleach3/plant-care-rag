"use client";

// The page's state and layout (architect-owned). Components receive state through props; none of them fetch.
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { ask, fetchSources, MAX_QUESTION, toAskError } from "@/lib/api";
import { clearThreads, loadThreads, saveThread } from "@/lib/history";
import type { Drawer, Genus, Sources, SourcesState, Thread as ThreadData, Turn } from "@/lib/types";
import { Composer } from "./Composer";
import { HistoryDrawer } from "./HistoryDrawer";
import { LibraryDrawer } from "./LibraryDrawer";
import { Rail } from "./Rail";
import { SourcesPanel } from "./SourcesPanel";
import { Thread } from "./Thread";
import { Welcome } from "./Welcome";

// Media queries read the browser's default rem (16px), not the scaled root: this is 1280px.
const WIDE = "(min-width: 80rem)";
const subscribeWide = (onChange: () => void) => {
  const query = matchMedia(WIDE);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
};

// crypto.randomUUID needs a secure context; a LAN address over http is not one.
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
const newThread = (): ThreadData => ({ id: uid(), createdAt: new Date().toISOString(), turns: [] });

export function Chat() {
  const [sources, setSources] = useState<Sources | null>(null);
  const [sourcesState, setSourcesState] = useState<SourcesState>("loading");
  const [thread, setThread] = useState<ThreadData>(newThread);
  const [threads, setThreads] = useState<ThreadData[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [genus, setGenus] = useState<Genus | null>(null);
  const [draft, setDraft] = useState("");
  const [drawer, setDrawer] = useState<Drawer>(null);
  const inflight = useRef<AbortController | null>(null);
  const fixture = useRef(false); // a seeded dev state is never written to history
  const wide = useSyncExternalStore(subscribeWide, () => matchMedia(WIDE).matches, () => true);

  const connect = (signal?: AbortSignal) =>
    fetchSources(signal).then(
      (s) => {
        setSources(s);
        setSourcesState("ready");
      },
      () => {
        if (!signal?.aborted) setSourcesState("offline");
      },
    );

  useEffect(() => {
    const name = process.env.NODE_ENV === "development" ? new URLSearchParams(location.search).get("fixture") : null;
    if (name) {
      fixture.current = true;
      import("@/lib/fixtures").then(({ seed }) => {
        const s = seed(name);
        if (!s) return;
        setSources(s.sources);
        setSourcesState(s.sourcesState);
        if (s.thread) {
          setThread(s.thread);
          setActiveId(s.thread.turns.at(-1)?.id ?? null);
        }
        if (s.threads) setThreads(s.threads);
        if (s.drawer) setDrawer(s.drawer);
      });
      return;
    }
    const ctl = new AbortController();
    connect(ctl.signal);
    return () => ctl.abort();
  }, []);

  const pending = thread.turns.some((t) => t.status === "pending");

  useEffect(() => {
    if (!fixture.current && !pending) saveThread(thread);
  }, [thread, pending]);

  const settle = (threadId: string, turnId: string, patch: Partial<Turn>) =>
    setThread((t) => (t.id !== threadId ? t : { ...t, turns: t.turns.map((x) => (x.id === turnId ? { ...x, ...patch } : x)) }));

  const run = (threadId: string, turn: Turn) => {
    const ctl = new AbortController();
    inflight.current = ctl;
    ask(turn.question, turn.genus, ctl.signal).then(
      (response) => settle(threadId, turn.id, { status: "done", response, error: undefined }),
      (err) => {
        if (!ctl.signal.aborted) settle(threadId, turn.id, { status: "error", error: toAskError(err) });
      },
    );
  };

  const canAsk = !pending && sourcesState !== "offline";

  const submit = (text: string) => {
    const question = text.trim();
    if (!question || question.length > MAX_QUESTION || !canAsk) return;
    const turn: Turn = { id: uid(), question, genus, askedAt: new Date().toISOString(), status: "pending" };
    setThread((t) => ({ ...t, turns: [...t.turns, turn] }));
    setActiveId(turn.id);
    setDraft("");
    run(thread.id, turn);
  };

  const retry = (turnId: string) => {
    const turn = thread.turns.find((t) => t.id === turnId);
    if (!turn || !canAsk) return;
    const again: Turn = { ...turn, status: "pending", error: undefined, askedAt: new Date().toISOString() };
    settle(thread.id, turnId, again);
    setActiveId(turnId);
    run(thread.id, again);
  };

  // Leaving a thread abandons its unanswered question: the service still finishes it, the UI stops waiting.
  const leave = (next: ThreadData) => {
    inflight.current?.abort();
    setThread(next);
    setActiveId(next.turns.at(-1)?.id ?? null);
    setDraft("");
    setDrawer(null);
  };

  const openDrawer = (d: "history" | "library") => {
    if (d === "history" && !fixture.current) setThreads(loadThreads());
    setDrawer(d);
  };

  const reconnect = () => {
    setSourcesState("loading");
    connect();
  };

  const titles = useMemo(() => new Map(sources?.notes.map((n) => [n.slug, n.title]) ?? []), [sources]);
  const corpus = sources
    ? { notes: sources.notes.length, sections: sources.notes.reduce((n, note) => n + note.sections.length, 0) }
    : null;
  const activeTurn = thread.turns.find((t) => t.id === activeId) ?? thread.turns.at(-1) ?? null;
  const welcome = thread.turns.length === 0;

  const composer = (variant: "welcome" | "docked") => (
    <Composer
      variant={variant}
      value={draft}
      onChange={setDraft}
      onSubmit={() => submit(draft)}
      genus={genus}
      onGenus={setGenus}
      pending={pending}
      sourcesState={sourcesState}
      corpus={corpus}
      onReconnect={reconnect}
    />
  );

  return (
    // data-ready: the first load settled (sources answered or failed, or a fixture seeded); the sweep waits on it.
    <div
      data-ready={sourcesState !== "loading" || undefined}
      className="mx-auto flex h-dvh w-full max-w-[128rem] flex-col md:flex-row"
    >
      <Rail drawer={drawer} onNewChat={() => leave(newThread())} onOpen={openDrawer} />
      <main className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        {welcome ? (
          <Welcome onPick={submit} disabled={!canAsk} composer={composer("welcome")} />
        ) : (
          <>
            <Thread
              turns={thread.turns}
              activeId={activeTurn?.id ?? null}
              onActivate={setActiveId}
              onRetry={retry}
              busy={!canAsk}
              titles={titles}
              inlineSources={!wide}
            />
            {composer("docked")}
          </>
        )}
      </main>
      {wide && !welcome && (
        <aside aria-label="Sources" className="w-[25.25rem] shrink-0 overflow-y-auto">
          <SourcesPanel turn={activeTurn} titles={titles} />
        </aside>
      )}
      <HistoryDrawer
        open={drawer === "history"}
        onClose={() => setDrawer(null)}
        threads={threads}
        onOpenThread={leave}
        onClear={() => {
          clearThreads();
          setThreads([]);
        }}
      />
      <LibraryDrawer
        open={drawer === "library"}
        onClose={() => setDrawer(null)}
        sources={sources}
        sourcesState={sourcesState}
        onReconnect={reconnect}
      />
    </div>
  );
}
