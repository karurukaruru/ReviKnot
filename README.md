# ReviKnot

**Compatibility checks your coding agent can call before an SDK change reaches production.**

Local version 0.6.0. [简体中文](README.zh-CN.md) · [MCP setup](MCP.md) · [Executed evidence](RELEASE_REVIEW_060_ZH.md) · [Submission actions](FINAL_REMAINING_ZH.md)

An adapter can silently lose tool-call IDs or change nested arguments while its
output is still valid JSON. ReviKnot checks the captured output against the
original input contract. Even identical outputs do not establish compatibility
when both were already broken.

## Use it in your coding workflow

Capture the affected message boundary after changing an adapter or upgrading
an SDK. Your coding agent can call four local MCP tools to inspect it, compare
recordings and export a standalone regression gate. Failures identify field
paths. Check the repaired capture again and keep the gate in CI.

From an extracted source checkout, Python 3.11+:

```sh
python -m pip install -e ".[mcp]"
python -m reviknot mcp --workspace .
```

The server waits on stdio for its host. [MCP.md](MCP.md) provides the actual
Codex registration command and tool arguments. No global editor configuration
is changed silently. The host chooses when to invoke checks; this release does
not claim continuous background monitoring or a recorded editor session.

## Try it without any model key

```sh
python -m reviknot demo --output outputs/my-demo
python -m reviknot serve outputs/my-demo
python examples/refund-agent/capture.py --output outputs/my-refund-case
```

The demo records controlled cases and intentionally retains failures. The
refund example has two tool calls, nested booleans, Unicode, currency and an
approval requirement. Lost IDs FAIL, preserved input PASS, false-to-zero
mutation FAIL. It is synthetic local data; no customer or payment system runs.
The base CLI supports Python 3.10+; optional MCP uses Python 3.11+.

## NVIDIA repair workflow

An explicitly selected NVIDIA model proposes a bounded declarative mapping.
Independent checks and a deliberately damaged mapping challenge it before the
actual tool conversation is allowed to succeed. Arbitrary model Python is not
executed. Keep credentials in an ignored local `.env.local`:

```sh
python -m reviknot --env-file .env.local live --provider nebius --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B --budget outputs/my-budget.json --output outputs/my-new-live-run
```

This command makes paid provider requests. MCP checks, saved replay and
exported gates do not. Request/output/context limits are configurable;
[OUTPUT_SETTINGS_ZH.md](OUTPUT_SETTINGS_ZH.md) explains their scope and audit
trail. [Full source review](SOURCE_REVIEW.md) is a separate chunked workflow.

## What was actually executed

- 0.6.0 NVIDIA Nemotron on Nebius Token Factory: 4 model calls, 5992
reported tokens, 8 checks, corrupted repair rejected, controlled health check 21.
- Official MCP SDK 2.3.0 client → stdio: 4 tools, 6 calls; independent exported gate
exits 1/0/1 for broken/fixed/corrupt captures. [Original MCP evidence](evidence/mcp-060/mcp-workflow.json).
- Real installed NVIDIA SDK 1.4.3/1.5.0 workers are a separate credited historical
case. Equal broken outputs remain NEEDS_REVIEW. [SDK execution](UPGRADE_RUN.md).
- Current tests and release checks are recorded in [RELEASE_REVIEW_060_ZH.md](RELEASE_REVIEW_060_ZH.md).

The checker covers reviewed text/tool-message schemas, not every SDK or
arbitrary project code. Redacted/unsupported captures do not earn PASS. Hashes
detect changes but do not authenticate a producer. Historical failures and the
small developer-authored PARTIAL benchmark remain available; no universal
accuracy or comparative performance claim is made.

## Development and judging

```sh
python -m pip install pytest pytest-subtests
python -m pytest
```

The free judge portal and standard-library gates require no model account.
Fresh MCP use needs its optional SDK; fresh NVIDIA generation needs lawful API
access. See [JUDGE_TESTING.md](JUDGE_TESTING.md). This iteration is local, not yet
published or submitted. [MIT license](LICENSE); credited source and third-party
notices remain with their evidence. Legacy `patchcourt` and `acv` entry points
are retained for compatibility; the product name is ReviKnot.

Repository: https://github.com/karurukaruru/ReviKnot
Blog: https://karuru.top · X: https://x.com/djkaruru
