# Eval report: v3

Config: mode=vector · k=5 · decompose=True · embed_model=BAAI/bge-base-en-v1.5 · llm_backend=cc · llm_model=claude-sonnet-5 · effort=low · code_sha=7aa48107407a · sql_sha=6c077bf9564a · chunks_sha=b015aee15638 · questions_sha=bf1b3b20e24b
Models seen: claude-sonnet-5 · gold: questions sha b7d66cf7e754

- dev: 23 questions; rows per rep: rep 1 23

Recall@k counts a required fact as found when any chunk in its gold group is retrieved. Hallucination = answered a must-refuse question; false refusal = refused an answerable one; error rows are excluded from both and listed by kind. Accuracy covers answerable questions: Keegan's manual grade (correct / partial / wrong) for each answer, a refusal counted as wrong; unfaithful = graded answers he marked as saying something not in his notes; narrates = answers that talk about notes or passages instead of the plant; inline ids = answers with a [doc#section] marker in the text (since prompt v2 the citations list carries them). Latency covers the timed (non-error) rows; P95 needs 10 of them.

| split | category | n | recall@k | accuracy | unfaithful | narrates | inline ids | hallucination | false refusal | errors | timed | P50 total ms | P95 total ms | P50 generate ms | P95 generate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | all | 23 | 0.95 (n=14) | 13 c, 0 p, 0 w, 1 ungraded | 0/13 | 1/14 | 0/14 | 0/9 | 0/14 | 0 | 23 | 7773 | 33747 | 7747 | 33715 |
| dev | factual | 8 | 1.00 (n=8) | 8 c, 0 p, 0 w | 0/8 | 0/8 | 0/8 | — | 0/8 | 0 | 8 | 10412 | — | 10351 | — |
| dev | multi-hop | 6 | 0.88 (n=6) | 5 c, 0 p, 0 w, 1 ungraded | 0/5 | 1/6 | 0/6 | — | 0/6 | 0 | 6 | 17239 | — | 17178 | — |
| dev | oos-near | 6 | — | — | — | — | — | 0/6 | — | 0 | 6 | 7141 | — | 7108 | — |
| dev | oos-far | 3 | — | — | — | — | — | 0/3 | — | 0 | 3 | 6286 | — | 6244 | — |

## Dev questions

| id | category | rep | recall@k | outcome | total ms |
|---|---|---|---|---|---|
| f01 | factual | 1 | 1.00 | answered | 10203 |
| f03 | factual | 1 | 1.00 | answered | 22508 |
| f04 | factual | 1 | 1.00 | answered | 34996 |
| f07 | factual | 1 | 1.00 | answered | 8837 |
| f09 | factual | 1 | 1.00 | answered | 7633 |
| f11 | factual | 1 | 1.00 | answered | 11725 |
| f12 | factual | 1 | 1.00 | answered | 10620 |
| f13 | factual | 1 | 1.00 | answered | 6964 |
| m02 | multi-hop | 1 | 1.00 | answered | 16840 |
| m04 | multi-hop | 1 | 0.50 | answered | 17638 |
| m05 | multi-hop | 1 | 1.00 | answered | 7166 |
| m06 | multi-hop | 1 | 1.00 | answered | 14865 |
| m09 | multi-hop | 1 | 1.00 | answered | 17844 |
| m10 | multi-hop | 1 | 0.75 | answered | 44251 |
| n01 | oos-near | 1 | — | refused | 6698 |
| n02 | oos-near | 1 | — | refused | 4675 |
| n03 | oos-near | 1 | — | refused | 7773 |
| n04 | oos-near | 1 | — | refused | 6946 |
| n05 | oos-near | 1 | — | refused | 7335 |
| n10 | oos-near | 1 | — | refused | 7656 |
| x02 | oos-far | 1 | — | refused | 7144 |
| x03 | oos-far | 1 | — | refused | 5644 |
| x04 | oos-far | 1 | — | refused | 6286 |
