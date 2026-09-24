# Eval report: v1

Config: mode=vector · k=5 · embed_model=BAAI/bge-base-en-v1.5 · llm_backend=cc · llm_model=claude-sonnet-5 · effort=low · code_sha=80de0f4af2d4 · sql_sha=663f89bf6e8b · chunks_sha=1d71502230ee · questions_sha=bf1b3b20e24b
Models seen: claude-sonnet-5 · gold: questions sha 71a55c069e52

- dev: 23 questions; rows per rep: rep 1 23

Recall@k counts a required fact as found when any chunk in its gold group is retrieved. Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying something not in his notes; narrates = answers that talk about notes or passages instead of the plant. Latency covers the timed (non-error) rows; P95 needs 10 of them.

| split | category | n | recall@k | accuracy | unfaithful | narrates | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | all | 23 | 0.91 (n=14) | 0 c, 0 p, 0 w, 14 ungraded | — | 0/14 | 0/9 | 0/14 | 0 | 23 | 8641 | 20211 | 8619 | 20185 |
| dev | factual | 8 | 1.00 (n=8) | 0 c, 0 p, 0 w, 8 ungraded | — | 0/8 | — | 0/8 | 0 | 8 | 10555 | — | 10529 | — |
| dev | multi-hop | 6 | 0.79 (n=6) | 0 c, 0 p, 0 w, 6 ungraded | — | 0/6 | — | 0/6 | 0 | 6 | 14166 | — | 14141 | — |
| dev | oos-near | 6 | — | — | — | — | 0/6 | — | 0 | 6 | 7109 | — | 7085 | — |
| dev | oos-far | 3 | — | — | — | — | 0/3 | — | 0 | 3 | 6284 | — | 6263 | — |

## Dev questions

| id | category | rep | recall@k | outcome | total ms |
|---|---|---|---|---|---|
| f01 | factual | 1 | 1.00 | answered | 12615 |
| f03 | factual | 1 | 1.00 | answered | 11922 |
| f04 | factual | 1 | 1.00 | answered | 40547 |
| f07 | factual | 1 | 1.00 | answered | 8641 |
| f09 | factual | 1 | 1.00 | answered | 6744 |
| f11 | factual | 1 | 1.00 | answered | 11344 |
| f12 | factual | 1 | 1.00 | answered | 9766 |
| f13 | factual | 1 | 1.00 | answered | 6061 |
| m02 | multi-hop | 1 | 1.00 | answered | 18750 |
| m04 | multi-hop | 1 | 0.00 | answered | 12392 |
| m05 | multi-hop | 1 | 1.00 | answered | 5073 |
| m06 | multi-hop | 1 | 1.00 | answered | 13933 |
| m09 | multi-hop | 1 | 1.00 | answered | 14398 |
| m10 | multi-hop | 1 | 0.75 | answered | 20374 |
| n01 | oos-near | 1 | — | refused | 7636 |
| n02 | oos-near | 1 | — | refused | 4376 |
| n03 | oos-near | 1 | — | refused | 6581 |
| n04 | oos-near | 1 | — | refused | 6411 |
| n05 | oos-near | 1 | — | refused | 9657 |
| n10 | oos-near | 1 | — | refused | 8236 |
| x02 | oos-far | 1 | — | refused | 4766 |
| x03 | oos-far | 1 | — | refused | 6284 |
| x04 | oos-far | 1 | — | refused | 6656 |
