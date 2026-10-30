# ReviKnot — Compatibility checks your coding agent can call

## The problem
A tool-using agent can break after an SDK or adapter change even when its tools still run. Lost call IDs orphan the results; a valid JSON conversion can also silently change nested arguments. Comparing two versions is insufficient when both outputs already violate the original input.

## What ReviKnot does
ReviKnot checks captured messages against the original input contract and gives the coding agent precise finding paths. Four local MCP tools inspect a boundary, check a recording, compare recorded versions and export a portable regression gate. Use it after editing message serialization or upgrading an SDK, before proposing a merge. The host chooses when to invoke it; there is no continuous polling or automatic editor trigger claimed.

The NVIDIA model workflow separately proposes a bounded declarative repair, challenges it independently and runs the actual model/tool conversation. A model cannot approve its own mapping. Python runs the checks, local interface, isolated SDK workers and CLI. Credentials remain outside public artifacts.

## Actual execution
NVIDIA-Nemotron-3-Nano-30B-A3B ran on Nebius Token Factory in the recorded 0.6.0 acceptance: four model calls, 5,992 reported tokens, eight independent repair checks, corrupted-repair rejection and a verified two-tool health check returning 21 from local quantity 3 and price 7. The arithmetic is a diagnostic fixture, not the product's main use case. Tavily retrieved supporting documentation.

The official MCP SDK 2.3.0 client launched the real stdio server, discovered all four tools and made six tool calls. A controlled refund-agent example includes two tools, nested booleans, Unicode, currency and an approval requirement: lost IDs FAIL, reviewed capture PASS, a false-to-zero mutation FAIL. Identical broken captures remain NEEDS_REVIEW. The exported standard-library gate then runs in isolated Python with expected broken/fixed/corrupt exits 1/0/1. This uses local synthetic data and never sends money. Actual installed NVIDIA SDK 1.4.3/1.5.0 evidence is a separate credited case.

The 0.6.1 source release adds the streamlined installer, default MCP dependency, client configuration setup and updated onboarding. These packaging changes do not represent a new paid model run; the model/MCP execution figures above remain tied to the 0.6.0 acceptance.

## Why use it
Keep the invariant that matters to your agent, inspect exactly what an adapter changed, and retain a regression test that a later developer or CI can rerun. MCP checks and exported gates require no model key or paid inference. They do not import arbitrary project code. A coding host can call the same checker as part of its existing edit/test workflow; host-specific setup instructions are provided, while this release was integration-tested with the official client.

## Scope and next steps
This is scoped text/tool-message contract verification, not universal code review or an arbitrary-code sandbox. Historical failed NVIDIA runs remain; the earlier small developer-authored benchmark remains PARTIAL. No broad accuracy, latency or cost advantage is claimed. Future work includes more independent adapter cases and editor-host usability studies.

Built With: Python; NVIDIA Nemotron 3 Nano 30B A3B; Nebius Token Factory; Tavily; Model Context Protocol; Remotion for the film.

Track: Coding and Agentic Engineering.
Repository: https://github.com/karurukaruru/ReviKnot (0.6.1 source release).
Blog: https://karuru.top · X: https://x.com/djkaruru
