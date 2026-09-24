# v1 — prompt v1: answer voice

Change: `prompts/answer.md` only. Answer first, talk to the grower, never mention notes or passages except in the exact
refusal, no greetings or sign-offs, plain words, no stock AI vocabulary; rule 4 states a gap as a fact about the plant.
Why: v0 graded m10 partial for answer voice, and 3 of 14 v0 answers talked about "the notes" instead of the plant.
Result: Keegan preferred v1 on 12 of 14 dev questions, blind (sign test p = 0.0129, `uv run python -m eval.compare v0.1 v1`).
Commits: `ed779ee` (prompt), `a873eea` (run), `015b48e` (comparison). Numbers: [report.md](report.md).
