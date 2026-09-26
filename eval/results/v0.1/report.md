# Eval report: v0.1

Config: mode=vector · k=5 · embed_model=BAAI/bge-base-en-v1.5 · llm_backend=cc · llm_model=claude-sonnet-5 · effort=low · code_sha=45c166ea9710 · sql_sha=663f89bf6e8b · chunks_sha=1d71502230ee · questions_sha=bf1b3b20e24b
Models seen: claude-sonnet-5 · gold: questions sha b7d66cf7e754

- dev: 23 questions; rows per rep: rep 1 23

Recall@k counts a required fact as found when any chunk in its gold group is retrieved. Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying something not in his notes; narrates = answers that talk about notes or passages instead of the plant; inline ids = answers with a [doc#section] marker in the text (since prompt v2 the citations list carries them). Latency covers the timed (non-error) rows; P95 needs 10 of them.

| split | category | n | recall@k | accuracy | unfaithful | narrates | inline ids | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | all | 23 | 0.91 (n=14) | 0 c, 0 p, 0 w, 14 ungraded | — | 2/14 | 7/14 | 0/9 | 0/14 | 0 | 23 | 9084 | 18183 | 9058 | 18156 |
| dev | factual | 8 | 1.00 (n=8) | 0 c, 0 p, 0 w, 8 ungraded | — | 0/8 | 3/8 | — | 0/8 | 0 | 8 | 11715 | — | 11693 | — |
| dev | multi-hop | 6 | 0.79 (n=6) | 0 c, 0 p, 0 w, 6 ungraded | — | 2/6 | 4/6 | — | 0/6 | 0 | 6 | 11980 | — | 11954 | — |
| dev | oos-near | 6 | — | — | — | — | — | 0/6 | — | 0 | 6 | 5786 | — | 5763 | — |
| dev | oos-far | 3 | — | — | — | — | — | 0/3 | — | 0 | 3 | 7043 | — | 7022 | — |

## Dev questions

| id | category | rep | recall@k | outcome | total ms |
|---|---|---|---|---|---|
| f01 | factual | 1 | 1.00 | answered | 16450 |
| f03 | factual | 1 | 1.00 | answered | 17421 |
| f04 | factual | 1 | 1.00 | answered | 9785 |
| f07 | factual | 1 | 1.00 | answered | 9613 |
| f09 | factual | 1 | 1.00 | answered | 7082 |
| f11 | factual | 1 | 1.00 | answered | 13646 |
| f12 | factual | 1 | 1.00 | answered | 8556 |
| f13 | factual | 1 | 1.00 | answered | 14554 |
| m02 | multi-hop | 1 | 1.00 | answered | 12009 |
| m04 | multi-hop | 1 | 0.00 | answered | 11317 |
| m05 | multi-hop | 1 | 1.00 | answered | 7306 |
| m06 | multi-hop | 1 | 1.00 | answered | 24254 |
| m09 | multi-hop | 1 | 1.00 | answered | 11952 |
| m10 | multi-hop | 1 | 0.75 | answered | 18268 |
| n01 | oos-near | 1 | — | refused | 6104 |
| n02 | oos-near | 1 | — | refused | 6061 |
| n03 | oos-near | 1 | — | refused | 7257 |
| n04 | oos-near | 1 | — | refused | 5031 |
| n05 | oos-near | 1 | — | refused | 4779 |
| n10 | oos-near | 1 | — | refused | 5510 |
| x02 | oos-far | 1 | — | refused | 9084 |
| x03 | oos-far | 1 | — | refused | 4726 |
| x04 | oos-far | 1 | — | refused | 7043 |
