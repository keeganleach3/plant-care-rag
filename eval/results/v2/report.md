# Eval report: v2

Config: mode=vector · k=5 · decompose=True · embed_model=BAAI/bge-base-en-v1.5 · llm_backend=cc · llm_model=claude-sonnet-5 · effort=low · code_sha=b33ecbd1a328 · sql_sha=663f89bf6e8b · chunks_sha=b015aee15638 · questions_sha=bf1b3b20e24b
Models seen: claude-sonnet-5 · gold: questions sha b7d66cf7e754

- dev: 23 questions; rows per rep: rep 1 23

Recall@k counts a required fact as found when any chunk in its gold group is retrieved. Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying something not in his notes; narrates = answers that talk about notes or passages instead of the plant; inline ids = answers with a [doc#section] marker in the text (since prompt v2 the citations list carries them). Latency covers the timed (non-error) rows; P95 needs 10 of them.

| split | category | n | recall@k | accuracy | unfaithful | narrates | inline ids | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | all | 23 | 0.95 (n=14) | 0 c, 0 p, 0 w, 14 ungraded | — | 0/14 | 6/14 | 0/9 | 0/14 | 0 | 23 | 9645 | 36672 | 9624 | 36647 |
| dev | factual | 8 | 1.00 (n=8) | 0 c, 0 p, 0 w, 8 ungraded | — | 0/8 | 3/8 | — | 0/8 | 0 | 8 | 11163 | — | 11143 | — |
| dev | multi-hop | 6 | 0.88 (n=6) | 0 c, 0 p, 0 w, 6 ungraded | — | 0/6 | 3/6 | — | 0/6 | 0 | 6 | 13150 | — | 13108 | — |
| dev | oos-near | 6 | — | — | — | — | — | 0/6 | — | 0 | 6 | 6201 | — | 6179 | — |
| dev | oos-far | 3 | — | — | — | — | — | 0/3 | — | 0 | 3 | 5815 | — | 5794 | — |

## Dev questions

| id | category | rep | recall@k | outcome | total ms |
|---|---|---|---|---|---|
| f01 | factual | 1 | 1.00 | answered | 11956 |
| f03 | factual | 1 | 1.00 | answered | 11730 |
| f04 | factual | 1 | 1.00 | answered | 49276 |
| f07 | factual | 1 | 1.00 | answered | 12438 |
| f09 | factual | 1 | 1.00 | answered | 8517 |
| f11 | factual | 1 | 1.00 | answered | 10596 |
| f12 | factual | 1 | 1.00 | answered | 10355 |
| f13 | factual | 1 | 1.00 | answered | 6234 |
| m02 | multi-hop | 1 | 1.00 | answered | 14347 |
| m04 | multi-hop | 1 | 0.50 | answered | 20214 |
| m05 | multi-hop | 1 | 1.00 | answered | 7081 |
| m06 | multi-hop | 1 | 1.00 | answered | 11952 |
| m09 | multi-hop | 1 | 1.00 | answered | 10703 |
| m10 | multi-hop | 1 | 0.75 | answered | 38501 |
| n01 | oos-near | 1 | — | refused | 6451 |
| n02 | oos-near | 1 | — | refused | 4903 |
| n03 | oos-near | 1 | — | refused | 5987 |
| n04 | oos-near | 1 | — | refused | 7843 |
| n05 | oos-near | 1 | — | refused | 5629 |
| n10 | oos-near | 1 | — | refused | 6415 |
| x02 | oos-far | 1 | — | refused | 9645 |
| x03 | oos-far | 1 | — | refused | 5585 |
| x04 | oos-far | 1 | — | refused | 5815 |
