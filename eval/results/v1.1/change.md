# v1.1 — re-baseline on today's corpus

Change: corpus only (no code). The plantlet feeding schedule (feed at planting, no fertilizer at the next watering,
then very light feeding) and "no need to turn the light up" from Keegan's v0.1-vs-v1 notes; f01 and m04 gold follow.
Why: a corpus edit moves embeddings, so the next retrieval change needs a baseline on the same chunks. It did move:
m06 lost the first-watering section (rank 4 to 7) because that section grew a sentence.
Commits: `f32e5f6` (corpus), `34b875b` (run). Numbers: [report.md](report.md).
