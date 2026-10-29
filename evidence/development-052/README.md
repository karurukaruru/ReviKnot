# Real development API records — 0.5.2

These are actual DeepSeek Flash/Tavily development requests. They do not
establish required NVIDIA model inference through Nebius.

| Directory | Result | Model requests | Reported total tokens | Scope |
|---|---|---:|---:|---|
| `deepseek-live-01` | PASS | 3 | 4094 | Initial 0.5.2 repair and fixture task; source later changed |
| `deepseek-reuse-01` | PASS | 2 | 655 | Initial exact knowledge hit, independently revalidated |
| `deepseek-evaluation-01` | PARTIAL | 6 | 19324 | Frozen v1, two trials of the same twelve developer-authored cases |
| `final-deepseek-live-01` | PASS | 3 | 4094 | Final provider/verification source, eight checks, corruption rejection and task result 21 |
| `final-deepseek-reuse-01` | PASS | 2 | 655 | Same final identity; actual knowledge hit, eight checks and task rerun |

The two pairs are separate executed runs, not additional benchmark examples.
Do not relabel the earlier identity as current. Current normalized verifier
source was separately compared against both final run identities in
`../tests/current-live-source-052.json`. In each pair, reuse skipped the new
repair-proposal request; two observations do not prove general savings.

The original-ACV arm in trial two of the evaluation reached its 2048 output
token limit and returned incomplete JSON. The system correctly rejected it and
retained the failure. C/D each matched 18/24 labels, with no observed retrieval
accuracy advantage. Some representation rules were underspecified in v1. The
new v2 prompt explicitly describes them and defaults to 8192 output tokens,
but **v2 has no real model score**. See
`../../docs/submission-052/EVALUATION_FINDINGS_EN_ZH.md`.

An additional real long-source test is at
`../source-review-052/deepseek-long-source-01`: two model requests, 37169 reported
tokens, complete responses covering all 63833 decoded characters. It uses a
synthetic credential-free fixture and is not a production benchmark or a
100000-real-input-token test. Its exact pre-final-security-fix module snapshot
and timing limitations are recorded in that directory's parent README.

This iteration used 18 model attempts and three basic searches. Together with
the prior seven model attempts/two searches, `budget-snapshot-final.json`
records **25/30 model attempts, 5/10 searches, 0/5 discoveries**. It is an audit
copy, not a fresh budget. The writable ledger remains
`outputs/submission-050/budget.json`; never reset it to a historical snapshot.
Reported tokens are not a dollar bill or an account-balance check.

No Nebius request, video production, email operation or remote publication was
performed in this iteration. Final required-platform feedback remains pending.
