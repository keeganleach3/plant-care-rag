# Eval report: v2.1

Config: mode=vector · k=5 · decompose=True · embed_model=BAAI/bge-base-en-v1.5 · llm_backend=cc · llm_model=claude-sonnet-5 · effort=low · code_sha=30ad8743dbb9 · sql_sha=407c32022094 · chunks_sha=b015aee15638 · questions_sha=bf1b3b20e24b
Models seen: claude-sonnet-5 · gold: questions sha b7d66cf7e754

- dev: 23 questions; rows per rep: rep 1 23

Recall@k counts a required fact as found when any chunk in its gold group is retrieved. Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying something not in his notes; narrates = answers that talk about notes or passages instead of the plant; inline ids = answers with a [doc#section] marker in the text (since prompt v2 the citations list carries them). Latency covers the timed (non-error) rows; P95 needs 10 of them.

| split | category | n | recall@k | accuracy | unfaithful | narrates | inline ids | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | all | 23 | 0.95 (n=14) | 0 c, 0 p, 0 w, 14 ungraded | — | 1/14 | 3/14 | 0/9 | 0/14 | 0 | 23 | 10959 | 37714 | 10895 | 37692 |
| dev | factual | 8 | 1.00 (n=8) | 0 c, 0 p, 0 w, 8 ungraded | — | 0/8 | 0/8 | — | 0/8 | 0 | 8 | 13694 | — | 13671 | — |
| dev | multi-hop | 6 | 0.88 (n=6) | 0 c, 0 p, 0 w, 6 ungraded | — | 1/6 | 3/6 | — | 0/6 | 0 | 6 | 13048 | — | 13026 | — |
| dev | oos-near | 6 | — | — | — | — | — | 0/6 | — | 0 | 6 | 5793 | — | 5771 | — |
| dev | oos-far | 3 | — | — | — | — | — | 0/3 | — | 0 | 3 | 4472 | — | 4452 | — |

## Dev questions

| id | category | rep | recall@k | outcome | total ms |
|---|---|---|---|---|---|
| f01 | factual | 1 | 1.00 | answered | 12846 |
| f03 | factual | 1 | 1.00 | answered | 14543 |
| f04 | factual | 1 | 1.00 | answered | 39710 |
| f07 | factual | 1 | 1.00 | answered | 18075 |
| f09 | factual | 1 | 1.00 | answered | 19754 |
| f11 | factual | 1 | 1.00 | answered | 12736 |
| f12 | factual | 1 | 1.00 | answered | 11218 |
| f13 | factual | 1 | 1.00 | answered | 6144 |
| m02 | multi-hop | 1 | 1.00 | answered | 11993 |
| m04 | multi-hop | 1 | 0.50 | answered | 51395 |
| m05 | multi-hop | 1 | 1.00 | answered | 5833 |
| m06 | multi-hop | 1 | 1.00 | answered | 10959 |
| m09 | multi-hop | 1 | 1.00 | answered | 14102 |
| m10 | multi-hop | 1 | 0.75 | answered | 16653 |
| n01 | oos-near | 1 | — | refused | 4245 |
| n02 | oos-near | 1 | — | refused | 6140 |
| n03 | oos-near | 1 | — | refused | 5695 |
| n04 | oos-near | 1 | — | refused | 5736 |
| n05 | oos-near | 1 | — | refused | 6627 |
| n10 | oos-near | 1 | — | refused | 5850 |
| x02 | oos-far | 1 | — | refused | 4472 |
| x03 | oos-far | 1 | — | refused | 7091 |
| x04 | oos-far | 1 | — | refused | 4421 |
