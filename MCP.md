# ReviKnot in a coding agent

[简体中文接入步骤](MCP.zh-CN.md)

ReviKnot exposes four local MCP tools. A coding agent can check captured
messages after editing an adapter or upgrading an SDK, inspect the finding
paths, then retain a standard-library regression gate before merging.
The host decides when to invoke a tool. This is not continuous background
monitoring, general source-code review, or automatic approval of a repair.

## Install and connect

Use Python3.11+ for the optional MCP SDK; the base CLI remains Python3.10+.

```sh
python -m pip install -e ".[mcp]"
python -m reviknot mcp --workspace /absolute/path/to/your/project
```

The second command serves stdio and waits for its host; it does not open a web
page. In Codex, register the installed Python executable as the server command:

```sh
codex mcp add reviknot -- /absolute/path/to/python -m reviknot mcp --workspace /absolute/path/to/your/project
```

Use an absolute interpreter path so the host uses the environment containing
ReviKnot and the optional SDK. A source checkout also needs a configured working
directory or an editable installation. Setup references: [official Codex MCP documentation](https://developers.openai.com/codex/mcp/) and [official Python MCP SDK](https://py.sdk.modelcontextprotocol.io/).
The command above is a setup instruction; this repository does not silently
change your global editor configuration.

## Tools

| Tool | Input | Result |
|---|---|---|
| inspect_boundary | input_path,output_path | Compare two message-array JSON files against the original input contract. |
| check_recording | recording_path, optional request_id | Check an explicitly selected BoundaryRecorder transaction. |
| compare_recordings | baseline_path,candidate_path, optional transaction IDs | Check both against the same input; identical broken output remains NEEDS_REVIEW. |
| export_regression_gate | recording_path, new output_dir, optional request_id | Export a standalone Python test and frozen checker; does not run it. |

Paths are relative to the configured workspace. The first three tools are
read-only. Export creates a new directory and preserves earlier evidence.
No tool calls a model, loads an env file, installs packages, runs application
code, or sends data to a remote service. Findings include exact paths and
explicit truncation counts. Default file limit8MB and100 reported findings
are configurable via `--max-file-bytes` and`--max-findings`.
Individual diagnostic fields default to2048 characters and can be configured
with `--max-finding-chars`; longer fields retain explicit truncation metadata,
original lengths and hashes instead of flooding the coding host's context.

The checker supports the reviewed text/tool-message schema. Unsupported or
redacted input does not earn PASS. Captures are user-supplied evidence; hashes
detect changes but do not authenticate an untrusted producer or establish that
a future SDK was executed.

## Capture your own boundary

```python
from patchcourt.recorder import BoundaryRecorder

recorder = BoundaryRecorder("my-adapter", "my-sdk-version")
payload, verdict = recorder.transform(messages, my_adapter, request_id="checkout-1")
recorder.save("artifacts/checkout.recording.json")
```

Choose the adapter explicitly and capture real input/output before changing
the candidate. A redacted capture is useful for debugging but cannot establish
full preservation of the original input. Review data before publishing.

Suggested instruction for your coding agent:

> After changing tool-message serialization or an SDK dependency, capture the
> affected boundary. Use ReviKnot to check it against the original input. Explain
> failed finding paths, capture the proposed fix again, and export a regression
> gate into a fresh directory before proposing the merge. Do not claim success
> from matching outputs if the baseline already fails its input contract.

## Reproduce the practical example

The [refund-agent example](examples/refund-agent/README.md) uses two tool calls,
nested booleans, Unicode, currency and an approval requirement. It demonstrates
an intentionally faulty application adapter, not an undisclosed SDK defect or
an actual payment service.

```sh
python examples/refund-agent/capture.py --output outputs/refund-example
python scripts/verify_mcp_workflow.py --output outputs/mcp-acceptance
```

Run the second command with the MCP-enabled interpreter. It launches the real
stdio server through the official SDK client, discovers all four tools,
checks broken/fixed/corrupt captures, verifies an unhealthy equal baseline,
exports a gate, rejects workspace escape, and executes that gate in isolated
Python. Broken/corrupt test exits1 and fixed exits0 are expected controls.

简体中文：在编辑器Agent完成相关修改或SDK升级后按需检查，不需要每隔几秒轮询。
它检查捕获消息的语义是否被保留，返回具体字段位置，并导出回归门禁。MCP检查不产生模型费用；
NVIDIA生成修复仍是单独的显式live流程。完整源码审查是另一个review-source命令，不能混称。
