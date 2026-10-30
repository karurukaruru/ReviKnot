# Testing and verification

## Current release: 0.6.1

The 0.6.1 release review records the following local verification:

- Full regression suite: **707 passed, 6 skipped, 201 subtests passed**, with no failures.
- Fresh-environment install and configuration checks: **34 passed, 1 skipped**.
- Real stdio MCP discovery found all four tools after default installation.
- The setup flow, configuration merge/backup behavior, repeatability and user-started web sessions were checked.
- No provider inference was required for these local checks.

See [RELEASE_REVIEW_061_ZH.md](RELEASE_REVIEW_061_ZH.md) for the exact environment and scope. The 0.6.1 review summary is the current test record; the raw text file below belongs to the preceding 0.6.0 source-only run, not the 0.6.1 count.

## Previous release: 0.6.0

The archived raw result is [pytest-full.txt](evidence/review-final-20261029/pytest-full.txt): **700 passed, 5 skipped, 201 subtests passed** on Windows with Python 3.12. It is retained as historical evidence and must not be presented as the 0.6.1 run.

## Run locally

Use Python 3.11+ for the complete application and install development dependencies:

    python -m pip install -e ".[dev]"
    python -m pytest -ra

Local loopback and child processes must be available. Some platform-specific tests may skip when the operating system does not permit symbolic links.

## Scope

Tests cover semantic message contracts, unsupported schemas and abstention, streaming reconstruction, redaction, evidence integrity, repair validation, CLI behavior, MCP stdio integration, setup/configuration, packaging and exported regression gates. Mock-provider tests are not real provider inference. A passing suite is evidence for tested behavior, not proof of bug freedom or universal framework compatibility.

For the actual recorded NVIDIA/Nebius model workflow, see the repository's current evidence and the release review. Do not infer new model execution from a local test pass.
