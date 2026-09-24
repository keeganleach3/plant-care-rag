# Eval report: v0

Config: mode=vector · k=5 · embed_model=BAAI/bge-base-en-v1.5 · llm_backend=cc · llm_model=claude-sonnet-5 · effort=low · code_sha=45c166ea9710 · sql_sha=663f89bf6e8b · chunks_sha=cc8702b90f1b · questions_sha=bf1b3b20e24b
Models seen: claude-sonnet-5 · gold: questions sha 1a25853522d9

- dev: 23 questions; rows per rep: rep 1 23

Recall@k counts a required fact as found when any chunk in its gold group is retrieved. Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying something not in his notes. Latency covers the timed (non-error) rows; P95 needs 10 of them.

| split | category | n | recall@k | accuracy | unfaithful | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | all | 23 | 0.91 (n=14) | 11 c, 3 p, 0 w | 0/14 | 0/9 | 0/14 | 0 | 23 | 7217 | 26167 | 7194 | 26141 |
| dev | factual | 8 | 1.00 (n=8) | 7 c, 1 p, 0 w | 0/8 | — | 0/8 | 0 | 8 | 11222 | — | 11190 | — |
| dev | multi-hop | 6 | 0.79 (n=6) | 4 c, 2 p, 0 w | 0/6 | — | 0/6 | 0 | 6 | 12220 | — | 12196 | — |
| dev | oos-near | 6 | — | — | — | 0/6 | — | 0 | 6 | 5810 | — | 5786 | — |
| dev | oos-far | 3 | — | — | — | 0/3 | — | 0 | 3 | 5028 | — | 5006 | — |

## Dev questions

| id | category | rep | recall@k | outcome | total ms |
|---|---|---|---|---|---|
| f01 | factual | 1 | 1.00 | answered | 15058 |
| f03 | factual | 1 | 1.00 | answered | 15532 |
| f04 | factual | 1 | 1.00 | answered | 32994 |
| f07 | factual | 1 | 1.00 | answered | 10140 |
| f09 | factual | 1 | 1.00 | answered | 9316 |
| f11 | factual | 1 | 1.00 | answered | 7089 |
| f12 | factual | 1 | 1.00 | answered | 12303 |
| f13 | factual | 1 | 1.00 | answered | 7217 |
| m02 | multi-hop | 1 | 1.00 | answered | 11103 |
| m04 | multi-hop | 1 | 0.00 | answered | 27349 |
| m05 | multi-hop | 1 | 1.00 | answered | 5110 |
| m06 | multi-hop | 1 | 1.00 | answered | 15366 |
| m09 | multi-hop | 1 | 1.00 | answered | 13337 |
| m10 | multi-hop | 1 | 0.75 | answered | 8154 |
| n01 | oos-near | 1 | — | refused | 4377 |
| n02 | oos-near | 1 | — | refused | 6123 |
| n03 | oos-near | 1 | — | refused | 5824 |
| n04 | oos-near | 1 | — | refused | 6897 |
| n05 | oos-near | 1 | — | refused | 5796 |
| n10 | oos-near | 1 | — | refused | 4536 |
| x02 | oos-far | 1 | — | refused | 5028 |
| x03 | oos-far | 1 | — | refused | 4786 |
| x04 | oos-far | 1 | — | refused | 6295 |
