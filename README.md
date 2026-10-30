# ReviKnot

**Valid JSON can still break an AI agent. Check the message contract before shipping an SDK change.**

[简体中文](README.zh-CN.md) · [Quick start](QUICKSTART.md) · [MCP integration](MCP.md) · [4K60 video](https://github.com/karurukaruru/ReviKnot/releases/download/v0.6.0/ReviKnot-96s-Demo.mp4)


> **Source note:** The published v0.6.1 release archive is a versioned snapshot from before the later documentation/evidence cleanup. For the currently curated source tree, clone the `main` branch. The runtime version remains 0.6.1.

ReviKnot checks whether an adapter preserves tool-call IDs, nested arguments and other message semantics. Your coding agent gets exact failure paths and can export a runnable regression test. Two equally broken outputs do not count as compatible.

This is the **complete MIT-licensed application**: MCP, CLI, local web interface, source review, provider workflows and regression exports are included. No separate restricted edition or unlock step. The small judge download is a convenient recorded example; [Releases](https://github.com/karurukaruru/ReviKnot/releases/latest) also provides the full source and installable application.

## Quick start: one command

Install Python **3.11+** for the complete application. Download and extract the latest source ZIP, or clone this repository. Open a terminal in the project folder:

    python setup_reviknot.py --open

This creates a local environment, installs **all runtime dependencies including MCP**, discovers all four tools over a real MCP connection, generates client configuration and opens **http://127.0.0.1:8765/**. No API key is needed. First installation needs internet access for packages. Stop the server with Ctrl+C. On macOS/Linux use python3 if needed.

The example deliberately shows a broken adapter FAIL, preserved input PASS and a corrupted repair FAIL. Negative-control failures are expected.

## Connect your coding agent in one command

Select your client; all four tools are configured together:

| Client | Command | Result |
|---|---|---|
| Codex with its CLI installed | python setup_reviknot.py --client codex | Registers the verified interpreter using the official CLI. |
| Cursor | python setup_reviknot.py --client cursor | Merges this workspace's .cursor/mcp.json. |
| Claude Code | python setup_reviknot.py --client claude-code | Merges this workspace's .mcp.json. |
| Other MCP clients | python setup_reviknot.py | Generates .reviknot/mcp.json and .reviknot/codex.toml. |

Add --workspace /absolute/path/to/your/project for a different project. Unrelated server entries are preserved; changed configurations are backed up. Restart/reload your client and allow the project MCP server when prompted. [MCP.md](MCP.md) includes inputs and capture examples.

## Run without activating an environment

    python run_reviknot.py doctor
    python run_reviknot.py --help
    python run_reviknot.py review-source . --dry-run --output outputs/source-plan

doctor checks installed dependencies and discovers all four tools through real stdio. Source-review dry runs plan complete coverage without inference. Use a new output directory for each report.

Already managing an environment? **python -m pip install -e . installs the complete runtime**, then python -m reviknot setup --client codex connects it. The old [mcp] spelling is still compatible but no longer required. Python 3.10 retains legacy CLI compatibility; complete installation requires 3.11+.

## Your own model account

Copy .env.example to ignored .env.local, uncomment only the fields you use and set NEBIUS_API_KEY and an exact available NEBIUS_MODEL, then:

    python run_reviknot.py --env-file .env.local live --provider nebius --output outputs/my-live-run

This makes real provider requests. Playback, local checks, MCP and exported gates do not. Nebius Token Factory, DeepSeek and GLM workflows are included; Tavily search uses --tavily and your own TAVILY_API_KEY.

The web workbench permits unlimited **user-started sessions by default**; set --max-runs N if you want a session cap. Per-run requests, turns, output length and optional persistent budgets remain configurable. Full-source review defaults to a 100,000-token planning window and splits/compresses context as needed. Providers determine actual model context/output capacity. [Settings](OUTPUT_SETTINGS_ZH.md).

## Executed evidence and scope

- Recorded NVIDIA Nemotron 3 Nano on Nebius Token Factory: four model calls, 5,992 reported tokens, eight independent checks and a corrupted-repair negative control. This model acceptance was completed in 0.6.0 and remains the recorded execution evidence in the 0.6.1 source release.
- Official MCP SDK: all four tools and broken/fixed/corrupt exported gates with exit codes 1/0/1.
- Real installed NVIDIA SDK comparisons and source attribution are retained. [SDK case](UPGRADE_RUN.md) · [0.6.1 installation and acceptance review](RELEASE_REVIEW_061_ZH.md).
- The 96-second film shows the 0.6.0 evidence run. Version 0.6.1 improves installation and onboarding; it does not claim a new model run.

The checker covers reviewed text/tool-message schemas. Unsupported or redacted captures do not earn PASS. Source review is a separate model workflow. MCP does not silently monitor an editor or execute model-provided Python.

## Development

    python -m pip install -e ".[dev]"
    python -m pytest

[MIT license](LICENSE) · [Architecture](ARCHITECTURE.md) · [Judge instructions](JUDGE_TESTING.md)

GitHub: https://github.com/karurukaruru/ReviKnot · Blog: https://karuru.top · X: https://x.com/djkaruru
