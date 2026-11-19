# v3 — prompt v2: no chunk ids in the answer text

Change: `prompts/answer.md` rule 2 only. Chunk ids go in the `citations` list, never in the answer text; the
interface shows the citations beside the answer. Retrieval is v2's (vector, k=5, decompose).
Why: Keegan, 2026-09-25: "drop them and let the UI show the citation when we make it." Prompt v1 asked for a
`[chunk_id]` after every fact and the model complied in 3 to 6 of 14 answers per run.
Result: `uv run python -m eval.gate v2.1 v3` passes (recall identical, 0 errors, hallucinations or false refusals);
inline ids 3/14 → 0/14. Citations per answer 2.64 → 2.50: the two answers citing fewer sections (f09, f11) were read,
and every fact in them is in a section they cite; they draw on fewer sections (median answer 128.5 → 113 words).
Commits: `488f3e0` (metric), `8c69282` (prompt), this run. Numbers: [report.md](report.md).
