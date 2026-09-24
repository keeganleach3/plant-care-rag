# Eval report: v1.1

Config: mode=vector · k=5 · embed_model=BAAI/bge-base-en-v1.5 · llm_backend=cc · llm_model=claude-sonnet-5 · effort=low · code_sha=80de0f4af2d4 · sql_sha=663f89bf6e8b · chunks_sha=b015aee15638 · questions_sha=bf1b3b20e24b
Models seen: claude-sonnet-5 · gold: questions sha b7d66cf7e754

- dev: 23 questions; rows per rep: rep 1 23

Recall@k counts a required fact as found when any chunk in its gold group is retrieved. Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying something not in his notes; narrates = answers that talk about notes or passages instead of the plant. Latency covers the timed (non-error) rows; P95 needs 10 of them.

| split | category | n | recall@k | accuracy | unfaithful | narrates | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | all | 23 | 0.88 (n=14) | 0 c, 0 p, 0 w, 14 ungraded | — | 1/14 | 0/9 | 0/14 | 0 | 23 | 10215 | 25424 | 10191 | 25402 |
| dev | factual | 8 | 1.00 (n=8) | 0 c, 0 p, 0 w, 8 ungraded | — | 0/8 | — | 0/8 | 0 | 8 | 14596 | — | 14570 | — |
| dev | multi-hop | 6 | 0.71 (n=6) | 0 c, 0 p, 0 w, 6 ungraded | — | 1/6 | — | 0/6 | 0 | 6 | 12412 | — | 12387 | — |
| dev | oos-near | 6 | — | — | — | — | 0/6 | — | 0 | 6 | 6029 | — | 6005 | — |
| dev | oos-far | 3 | — | — | — | — | 0/3 | — | 0 | 3 | 6169 | — | 6147 | — |

## Dev questions

| id | category | rep | recall@k | outcome | total ms |
|---|---|---|---|---|---|
| f01 | factual | 1 | 1.00 | answered | 18299 |
| f03 | factual | 1 | 1.00 | answered | 27895 |
| f04 | factual | 1 | 1.00 | answered | 26052 |
| f07 | factual | 1 | 1.00 | answered | 15765 |
| f09 | factual | 1 | 1.00 | answered | 10215 |
| f11 | factual | 1 | 1.00 | answered | 13426 |
| f12 | factual | 1 | 1.00 | answered | 10765 |
| f13 | factual | 1 | 1.00 | answered | 7655 |
| m02 | multi-hop | 1 | 1.00 | answered | 18524 |
| m04 | multi-hop | 1 | 0.00 | answered | 14585 |
| m05 | multi-hop | 1 | 1.00 | answered | 6124 |
| m06 | multi-hop | 1 | 0.50 | answered | 10240 |
| m09 | multi-hop | 1 | 1.00 | answered | 9977 |
| m10 | multi-hop | 1 | 0.75 | answered | 19771 |
| n01 | oos-near | 1 | — | refused | 4553 |
| n02 | oos-near | 1 | — | refused | 7002 |
| n03 | oos-near | 1 | — | refused | 6463 |
| n04 | oos-near | 1 | — | refused | 4322 |
| n05 | oos-near | 1 | — | refused | 5595 |
| n10 | oos-near | 1 | — | refused | 6725 |
| x02 | oos-far | 1 | — | refused | 13154 |
| x03 | oos-far | 1 | — | refused | 6169 |
| x04 | oos-far | 1 | — | refused | 5828 |
