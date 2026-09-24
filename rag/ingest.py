"""corpus/*.md → chunks → embeddings → Postgres.  uv run python -m rag.ingest [--prune] [--corpus DIR]"""
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from rag import db
from rag.chunker import DocError, chunk, parse
from rag.config import CORPUS, settings
from rag.embed import Embedder


@dataclass
class Report:
    ingested: int = 0
    chunks: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (file, reason)
    pruned: int = 0


def run(corpus_dir: Path, conn, embedder: Embedder, prune: bool = False) -> Report:
    """All or nothing: every upsert and the prune share one transaction, so a failure mid-run leaves both tables as they
    were and a reader never sees a half-updated corpus."""
    report = Report()
    keep_chunks, keep_docs = set(), set()
    with conn.transaction():
        for path in sorted(p for p in corpus_dir.glob("*.md") if not p.name.startswith("_")):
            try:
                doc = parse(path)
            except DocError as exc:
                report.skipped.append((path.name, str(exc)))
                continue
            chunks = chunk(doc)
            if not chunks:
                report.skipped.append((path.name, "no H2 sections"))
                continue
            doc_id = db.upsert_document(conn, doc)
            db.upsert_chunks(conn, doc_id, chunks, embedder.embed_docs([c.content for c in chunks]), embedder.name)
            report.ingested += 1
            report.chunks += len(chunks)
            keep_docs.add(doc.slug)
            keep_chunks.update(c.chunk_id for c in chunks)
        if prune:
            report.pruned = db.prune(conn, keep_chunks, keep_docs)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--prune", action="store_true", help="delete chunks/documents no longer present in the corpus")
    args = ap.parse_args(argv)
    conn = db.connect()
    report = run(args.corpus, conn, Embedder(settings()["EMBED_MODEL"]), prune=args.prune)
    for name, reason in report.skipped:
        print(f"skip  {name}: {reason}", file=sys.stderr)
    print(f"ingested {report.ingested} docs, {report.chunks} chunks, pruned {report.pruned}, skipped {len(report.skipped)}")


if __name__ == "__main__":
    main()
