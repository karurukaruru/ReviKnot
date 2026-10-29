# ReviKnot — Stop silent agent regressions at the boundary

## Inspiration
An agent can call its tools correctly and still break on the next request: an SDK adapter silently drops tool-call identifiers. Ordinary version-to-version comparisons can miss this when both releases produce the same broken output.

## What it does
ReviKnot checks the original message contract, asks a model for a bounded declarative repair, challenges that repair independently, and executes the real model/tool conversation again. It retains rejected candidates and failed runs. A captured boundary can become a standalone Python regression gate for CI.

## How we built it
Python powers the CLI, local browser interface, semantic checks and isolated SDK workers. NVIDIA-Nemotron-3-Nano-30B-A3B runs through Nebius Token Factory for the repair proposal and actual tool conversation. Tavily retrieves supporting documentation. Model-generated mappings are data; arbitrary model Python is not executed. Exact source/environment identities scope repair reuse. Long-source review reads every supported source chunk before compacting findings. Runtime/output limits and persistent request budgets are user-configurable.

## Executed result
The final NVIDIA run used4 model requests and5631 reported tokens. All8 independent repair checks passed, an intentionally corrupted mapping was rejected, and two controlled local tools supplied quantity3 and price7; the actual model returned inventory_value21. Separate installed NVIDIA SDK1.4.3/1.5.0 runs demonstrate that equal broken outputs remain NEEDS_REVIEW. The exported CI gate fails for the broken/corrupted candidates and passes for the reviewed repair.

## Challenges and limits
We fixed metadata compatibility, strict JSON recovery, truncated/parallel action handling, inspected-source attribution and stream identifier handling. Two earlier NVIDIA runs remain preserved: one failed adapter-envelope validation; one exhausted the old shared request limit before its final summary. This is a narrow controlled boundary repair demonstration, not a general arbitrary-code sandbox or a claim that all SDK versions are defective. Historical bugs are attributed. The exploratory developer-authored benchmark remains PARTIAL; no universal accuracy or retrieval benefit is claimed.

## What's next
Broader independently authored SDK cases, richer user-captured boundaries and deployment feedback. Current artifacts include an API-free judge replay, source, installable wheel, regression gate and96-second demonstration. Public links must refer to the actual published0.5.3 artifacts.

Built With: Python; NVIDIA Nemotron3 Nano30B A3B; Nebius Token Factory; Tavily; HTML/CSS/JavaScript; Remotion (film).

Source repository: https://github.com/karurukaruru/agent-code-validator (publish current0.5.3 before submission).
X: https://x.com/djkaruru
