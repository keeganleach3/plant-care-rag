# v2 — decomposition of multi-question messages

Change: `--decompose`. A message is split at "?" and where and/or/also/plus opens a new question (fragments under
four words are dropped); the whole message and each clause are searched, and the rankings fused by reciprocal rank
(c=60, as in `hybrid_search`). One-question messages search exactly as before; no model call is added.
Why: m04 ("how long do they stay in the dome and when can i start feeding them") retrieved only dome sections;
the feeding section ranked 13th for the whole message and 1st for its second question.
Result: only m04 and m06 retrieve differently. m04 still misses the feeding section (known miss, see
[../../notes.md](../../notes.md)); a cross-encoder reranker was probed as the fix and rejected there.
Commits: `15a8dcb` (code), `b08fd7d` (run). Numbers: [report.md](report.md).
