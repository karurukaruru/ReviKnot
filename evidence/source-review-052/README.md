# Full-source review development test

`long_source_fixture.py` is an intentionally synthetic length/coverage fixture,
not an application or a user adoption example. It contains a long literal table
and an intentionally unsafe empty-list division near the end. It was never
imported or executed by the review pipeline.

`deepseek-long-source-01/` records two actual DeepSeek Flash requests and complete,
valid replies for all **63833 decoded characters**, including the tail. Windows
CRLFs are included in that count. Provider-reported total usage is **37169
tokens**, including input and output across both requests. This is not a claim
that 100000 actual input tokens were sent in one request.

The plan reserved a 100000-unit context budget and 8192 output tokens per request
using complete serialized request bytes as a conservative planning bound. The
second reply identified the deliberately unsafe division at the tail. All
suggestions, including the other stylistic suggestions, remain unverified model
output; this does not prove that the model understood every line.

`long-plan/` is the earlier free planning smoke, before the final prompt wording;
it sent no model request. It is retained rather than overwritten.

After the real run, independent offline review found a separate defect: a known
credential split at a chunk boundary could evade fragment-by-fragment redaction.
The final code redacts the entire source snapshot before splitting, preserving
character and line positions. Boundary, Unicode and CRLF regressions verify that
fix offline. The fixture in the real run has no credential, and its original
records are unchanged. **The paid run was not repeated after this safety fix.**
`execution-snapshot.json` and `executed-source-review.py.txt` preserve the module
bytes associated with that pre-fix real test. Final installed-wheel/CLI checks
are separately recorded under `../tests/`.

No NVIDIA/Nebius inference, arbitrary source execution or automatic patching is
established by this experiment. Scope and supported files: `../../SOURCE_REVIEW.md`.
