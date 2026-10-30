# ReviKnot judge testing

The current repository source version is 0.6.1. Build and publish the matching 0.6.1 judge-demo package before sharing a download URL; do not describe an older 0.6.0 package as the current source package. For the recorded portal, Windows users can double-click Start-Judge-Demo.cmd; other systems can run python launch_demo.py. Follow the included START-HERE instructions.

Replay, contract checks and exported standard-library gates need no account, API key or payment.

1. Inspect the recorded NVIDIA/Nebius repair acceptance: eight independent checks, a deliberately corrupted mapping rejected, and the controlled two-tool health check returning 21. This is saved 0.6.0 execution evidence included with the 0.6.1 source tree; playback sends no new inference requests.
2. Inspect the actual installed NVIDIA SDK 1.4.3/1.5.0 comparison. Two equally broken outputs remain NEEDS_REVIEW rather than being declared compatible.
3. Inspect MCP execution evidence: the official SDK client launched the real stdio server, discovered four tools and made six calls. The controlled refund-adapter sequence is FAIL/PASS/FAIL, and isolated exported-gate exits are 1/0/1. This is not a recording of a particular editor host.
4. To connect a coding host, use Python 3.11+ and follow MCP.md. MCP checks use explicitly supplied local captures, not provider keys.

Use examples/refund-agent/capture.py or capture your own explicitly selected adapter. A semantic PASS is scoped to the reviewed message schema; it is not a universal code-quality approval.

Fresh NVIDIA-generated repair is a separate opt-in live command and requires lawful provider access. Do not enter private keys into the static portal. Submission status and remaining entrant actions are documented in 06_Checklist_邮件逐项对照.md.

中文：录制回放、语义检查、门禁和 MCP 本地验证不需要 API Key；只有新的模型推理才需要合法 API。0.6.1 改善安装与接入，真实 NVIDIA 模型证据仍明确标注为 0.6.0 验收，不冒充新一轮实测。
