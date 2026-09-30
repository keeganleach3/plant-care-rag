// Development only (contract-chat-ui.md §6): `/?fixture=<name>` seeds a state for sweeps, route shots and building
// without the model. Chat.tsx loads this through a dynamic import behind a NODE_ENV check. Every answer is a recorded
// eval row from the DEV set (lib/fixtures/*.json name their source); never a holdout row.
import type { AskResponse, Drawer, Sources, SourcesState, Thread, Turn } from "./types";
import f11 from "./fixtures/f11.json";
import m06 from "./fixtures/m06.json";
import n03 from "./fixtures/n03.json";
import pending from "./fixtures/pending.json";
import snapshot from "./fixtures/sources.json";

export interface Seed {
  sources: Sources | null;
  sourcesState: SourcesState;
  thread?: Thread;
  threads?: Thread[];
  drawer?: Drawer;
}

type Recorded = { _source: string; _question: string } & Record<string, unknown>;

const ago = (seconds: number) => new Date(Date.now() - seconds * 1000).toISOString();

function done(fx: Recorded, secondsAgo: number): Turn {
  const { _source, _question, ...response } = fx;
  void _source;
  return {
    id: `fx-${_question.length}-${secondsAgo}`,
    question: _question,
    genus: null,
    askedAt: ago(secondsAgo),
    status: "done",
    response: response as unknown as AskResponse,
  };
}

const thread = (id: string, turns: Turn[]): Thread => ({ id, createdAt: turns[0].askedAt, turns });
const sources = snapshot as unknown as Sources;
const failed = (error: Turn["error"]): Turn => ({
  id: "fx-error",
  question: m06._question,
  genus: null,
  askedAt: ago(20),
  status: "error",
  error,
});

const SEEDS: Record<string, () => Omit<Seed, "sources" | "sourcesState">> = {
  answer: () => ({ thread: thread("fx-answer", [done(m06, 60)]) }),
  thread: () => ({ thread: thread("fx-thread", [done(f11, 300), done(m06, 60)]) }),
  refusal: () => ({ thread: thread("fx-refusal", [done(n03, 60)]) }),
  loading: () => ({
    thread: thread("fx-loading", [
      { id: "fx-pending", question: pending._question, genus: null, askedAt: ago(4), status: "pending" },
    ]),
  }),
  error: () => ({ thread: thread("fx-error", [failed({ kind: "generation", detail: "timeout", status: 502 })]) }),
  busy: () => ({ thread: thread("fx-busy", [failed({ kind: "busy", detail: "busy", status: 503, retryAfter: 5 })]) }),
  library: () => ({ drawer: "library" }),
  history: () => ({
    drawer: "history",
    threads: [
      thread("fx-h1", [done(f11, 300), done(m06, 240)]),
      thread("fx-h2", [done(n03, 86_400)]),
      thread("fx-h3", [done(m06, 3 * 86_400)]),
    ],
  }),
};

export function seed(name: string): Seed | null {
  if (name === "offline") return { sources: null, sourcesState: "offline" };
  const make = SEEDS[name];
  return make ? { sources, sourcesState: "ready", ...make() } : null;
}
