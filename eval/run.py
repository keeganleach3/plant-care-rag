"""Run the eval set through the served pipeline (rag.pipeline.ask): one results row per (question, rep).

  uv run python -m eval.run --version v0                  # dev split, vector, k=5, 1 rep
  uv run python -m eval.run --version v1 --mode hybrid
  uv run python -m eval.run --version v0 --report         # rebuild report.md from the results files only, no calls
eval/results/<version>/ holds config.json (frozen by the first run), results.jsonl (dev) and results.holdout.jsonl
(append-only; a rerun resumes and retries backend errors) and report.md. Never read results.holdout.jsonl row by row.
Nothing runs unless the question set validates against the live chunks table and the corpus.
"""
import argparse
import hashlib
import json
from collections import Counter
from functools import partial
from pathlib import Path

from eval import grade, questions
from rag import db, generate, pipeline, retrieve
from rag.config import CORPUS, PROMPTS, RESULTS, ROOT, settings
from rag.embed import Embedder

FILES = {"dev": "results.jsonl", "holdout": "results.holdout.jsonl"}
RETRY = ("cli_error", "timeout")  # backend failures say nothing about the system under test, so a rerun retries them
STOP_AFTER = 3                    # consecutive backend errors before a run gives up
P95_MIN = 10                      # below this many timed rows a P95 is just the max


class RunError(Exception):
    pass


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def _latest(out_dir: Path) -> dict:
    """Latest row per (id, rep) across both results files; earlier attempts stay in the files as history."""
    return {(r["id"], r["rep"]): r for name in FILES.values() for r in _jsonl(out_dir / name)}


def _freeze(out_dir: Path, config: dict) -> None:
    p = out_dir / "config.json"
    if p.exists():
        frozen = json.loads(p.read_text(encoding="utf-8"))
        diff = sorted(k for k in frozen.keys() | config.keys() if frozen.get(k) != config.get(k))
        if diff:
            raise RunError(f"{out_dir.name} was run with a different config ({', '.join(diff)}); use a new version name")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def run(out_dir: Path, rows: list[dict], ask, config: dict, *, reps: int = 1, log=print) -> int:
    """Append a row for every (question, rep) whose latest attempt is missing or a backend error; returns how many ran."""
    _freeze(out_dir, config)
    done = {key for key, r in _latest(out_dir).items() if not (r["error"] and r["error"]["kind"] in RETRY)}
    n = streak = 0
    for rep in range(1, reps + 1):
        for i, q in enumerate(rows, 1):
            if (q["id"], rep) in done:
                continue
            res = {"id": q["id"], "rep": rep, **ask(q["question"])}
            with (out_dir / FILES[q["split"]]).open("a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            n += 1
            err = res["error"]
            if q["split"] == "holdout":
                log(f"holdout rep{rep}: {i}/{len(rows)}")  # never an id or an outcome
            else:
                outcome = f"ERROR {err['kind']}" if err else ("refused" if res["refused"] else "answered")
                log(f"{q['id']} rep{rep}  {outcome:<24} recall={grade.grade(q, res)['recall']}  {res['timings']['total_ms']:.0f} ms")
            streak = streak + 1 if err and err["kind"] in RETRY else 0
            if streak == STOP_AFTER:
                raise RunError(f"{streak} consecutive {err['kind']} errors, last: {err['detail'][:200]}; "
                               "fix the backend and rerun, those rows are retried")
    return n


def _frac(pair):
    return "—" if not pair[1] else f"{pair[0]}/{pair[1]}"


def _num(v, fmt="{:.2f}"):
    return "—" if v is None else fmt.format(v)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def report(out_dir: Path, rows: list[dict]) -> str:
    """Rebuilt from the results files alone, each (question, rep) counted once as its latest attempt. Holdout shows
    only its overall row, so no single holdout question's outcome can steer a change."""
    if not (out_dir / "config.json").exists():
        raise RunError(f"no run recorded for {out_dir.name}")
    config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    pairs = [(by_id[r["id"]], r) for r in _latest(out_dir).values() if r["id"] in by_id]
    grades = {(g["id"], g["rep"]): g for g in _jsonl(out_dir / "grades.jsonl")}
    models = sorted({r["model"] for _, r in pairs if r.get("model")}) or ["—"]
    lines = [f"# Eval report: {out_dir.name}", "", "Config: " + " · ".join(f"{k}={v}" for k, v in config.items()),
             f"Models seen: {', '.join(models)} · gold: questions sha {_sha(json.dumps(rows, sort_keys=True))}", ""]
    for split in questions.SPLITS:
        reps = Counter(r["rep"] for q, r in pairs if q["split"] == split)
        if reps:
            lines.append(f"- {split}: {sum(q['split'] == split for q in rows)} questions; rows per rep: "
                         + ", ".join(f"rep {k} {v}" for k, v in sorted(reps.items())))
    lines += ["", "Recall@k counts a required fact as found when any chunk in its gold group is retrieved. "
              "Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are "
              f"excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / "
              "partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying "
              f"something not in his notes. Latency covers the timed (non-error) rows; P95 needs {P95_MIN} of them.", "",
              "| split | category | n | recall@k | accuracy | unfaithful | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for split in questions.SPLITS:
        in_split = [(q, r) for q, r in pairs if q["split"] == split]
        for cat in ("all",) + (questions.CATEGORIES if split == "dev" else ()):
            sel = in_split if cat == "all" else [(q, r) for q, r in in_split if q["category"] == cat]
            if not sel:
                continue
            s = grade.summarize(sel, grades)
            recall, n_recall = s["recall"]
            p95 = lambda key: _num(s[key], "{:.0f}") if s["timed"] >= P95_MIN else "—"
            acc = s["accuracy"]
            accuracy = "—" if not acc else ", ".join(f"{acc.get(k, 0)} {k}" for k in "cpw") + (f", {acc['ungraded']} ungraded" if acc.get("ungraded") else "")
            cells = [split, cat, s["n"], "—" if not n_recall else f"{recall:.2f} (n={n_recall})", accuracy, _frac(s["unfaithful"]),
                     _frac(s["hallucination"]),
                     _frac(s["false_refusal"]), ", ".join(f"{k} {v}" for k, v in sorted(s["errors"].items())) or "0",
                     s["timed"], _num(s["p50_total_ms"], "{:.0f}"), p95("p95_total_ms"),
                     _num(s["p50_generate_ms"], "{:.0f}"), p95("p95_generate_ms")]
            lines.append("| " + " | ".join(map(str, cells)) + " |")
    lines += ["", "## Dev questions", "", "| id | category | rep | recall@k | outcome | total ms |", "|---|---|---|---|---|---|"]
    for q, r in pairs:
        if q["split"] != "dev":
            continue
        g = grade.grade(q, r)
        outcome = f"error: {g['error']}" if g["error"] else ("refused" if r["refused"] else "answered")
        flag = " ✗" if g["hallucinated"] or g["false_refusal"] else ""
        lines.append(f"| {q['id']} | {q['category']} | {r['rep']} | {_num(g['recall'])} | {outcome}{flag} | {r['timings']['total_ms']:.0f} |")
    text = "\n".join(lines) + "\n"
    (out_dir / "report.md").write_text(text, encoding="utf-8")
    return text


def _code_sha() -> str:
    """Everything in rag/ and prompts/ that shapes an answer: retrieval SQL, embed prefixes, build_user, the prompt, timeouts."""
    files = sorted(p for p in [*(ROOT / "rag").glob("*.py"), *PROMPTS.glob("*")] if p.is_file())
    return _sha("".join(f"{p.relative_to(ROOT).as_posix()}\n{p.read_text(encoding='utf-8')}" for p in files))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--split", choices=questions.SPLITS, default="dev")
    ap.add_argument("--mode", choices=retrieve.MODES, default="vector")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--model", default=generate.MODEL)
    ap.add_argument("--effort", default=generate.EFFORT)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--report", action="store_true", help="rebuild report.md from the results files only")
    args = ap.parse_args(argv)
    out_dir, rows = RESULTS / args.version, questions.load()
    try:
        if not args.report:
            conn = db.connect()
            chunks = conn.execute("SELECT chunk_id, genus, topic, md5(content), md5(embedding::text) FROM chunks ORDER BY chunk_id").fetchall()
            bad = questions.problems(rows, {c[0] for c in chunks}, [p.read_text(encoding="utf-8") for p in CORPUS.glob("*.md")])
            if bad:
                raise SystemExit("question set failed validation:\n  " + "\n  ".join(bad))
            sql = conn.execute("SELECT string_agg(pg_get_functiondef(p.oid), ' ' ORDER BY p.oid) FROM pg_proc p "
                               "WHERE p.proname = 'hybrid_search'").fetchone()[0]
            cfg, k = settings(), max(1, min(args.k, 20))
            config = {"mode": args.mode, "k": k, "embed_model": cfg["EMBED_MODEL"], "llm_backend": cfg["LLM_BACKEND"],
                      "llm_model": args.model, "effort": args.effort, "code_sha": _code_sha(), "sql_sha": _sha(str(sql)),
                      "chunks_sha": _sha(json.dumps(chunks)),
                      "questions_sha": _sha(json.dumps(sorted((r["id"], r["question"]) for r in rows)))}
            ask = partial(pipeline.ask, conn, Embedder(cfg["EMBED_MODEL"]), k=k, mode=args.mode, model=args.model, effort=args.effort)
            print(f"ran {run(out_dir, [r for r in rows if r['split'] == args.split], ask, config, reps=args.reps)} new rows")
        print(report(out_dir, rows))
    except RunError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
