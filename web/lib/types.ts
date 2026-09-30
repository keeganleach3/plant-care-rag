// Shapes of the RAG service's responses (rag/api.py, rag/pipeline.py) and of the UI's own state.

export const GENERA = ["monstera", "alocasia", "anthurium", "philodendron"] as const;
export type Genus = (typeof GENERA)[number];

export interface Chunk {
  chunk_id: string; // "<note-slug>#<section-slug>"
  content: string;
  heading: string;
  genus: string;
  topic: string;
  score: number; // cosine in plain vector search, an RRF score when fused; never shown as a percentage
}

export interface AskResponse {
  params: { k: number; mode: "vector" | "hybrid"; genus: string | null; decompose: boolean };
  queries: string[]; // the whole message first, then its clauses
  chunks: Chunk[];
  answer: string;
  citations: string[];
  refused: boolean;
  model: string;
  timings: { embed_ms: number; retrieve_ms: number; generate_ms: number; total_ms: number };
}

// busy / db / embed_model: the service's 503 details. unreachable / timeout: the web proxy's own 503 and 504.
// generation: a 502, with the service's error kind in `detail`. rejected: 401 (RAG_API_KEY wrong or missing).
export type AskErrorKind = "busy" | "db" | "embed_model" | "unreachable" | "timeout" | "generation" | "rejected" | "unknown";

export interface AskError {
  kind: AskErrorKind;
  detail: string;
  status: number; // 0 when the web server itself could not be reached
  retryAfter?: number; // seconds
}

export interface Turn {
  id: string;
  question: string;
  genus: Genus | null;
  askedAt: string; // ISO time the question was sent
  status: "pending" | "done" | "error";
  response?: AskResponse;
  error?: AskError;
}

export interface Thread {
  id: string;
  createdAt: string;
  turns: Turn[];
}

export interface Section {
  chunk_id: string;
  heading: string;
  content: string;
}

export interface Note {
  slug: string;
  title: string;
  genus: string; // a genus, or "general"
  topic: string;
  sections: Section[];
}

export interface Sources {
  embed_model: string;
  notes: Note[];
}

export type SourcesState = "loading" | "ready" | "offline";
export type Drawer = "history" | "library" | null;
