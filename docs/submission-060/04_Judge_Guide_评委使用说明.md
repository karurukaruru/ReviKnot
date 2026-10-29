# ReviKnot judge testing

Download and extract ReviKnot-Judge-Demo-0.6.0.zip. For the recorded portal,
Windows double-click Start-Judge-Demo.cmd; other systems run python launch_demo.py.
Python3.10+ is sufficient. No account, key or payment is needed for replay,
contract checks or the exported standard-library gates.

1. Inspect the actual saved NVIDIA repair:8 checks, corrupted mapping rejected,
task health check21. Playback sends no new inference requests.
2. Inspect actual installed SDK1.4.3/1.5.0 evidence: two equally broken outputs
remain NEEDS_REVIEW. This is a credited historical defect, not a new discovery.
3. Inspect MCP execution evidence: official SDK client over real stdio,
4 discovered tools,6 calls, controlled refund-adapter FAIL/PASS/FAIL and
isolated gate exits1/0/1. This is not a recording of a particular editor host.
4. Install the included wheel and the optional MCP SDK in Python3.11+ to connect
your coding host. See MCP.md. MCP checks use supplied local captures, not keys.
Use examples/refund-agent/capture.py or capture your own explicitly selected
adapter; a semantic PASS is scoped to the reviewed message schema.

Fresh NVIDIA-generated repair is a separate opt-in live command and requires
lawful provider access. Do not enter private keys into the static portal.
See FINAL_REMAINING_ZH.md for publication, judging access and entrant steps.

中文：录制回放、语义检查、门禁和MCP本地验证免费；只有新的模型修复才需要合法API。
本轮用官方MCP客户端做了真正stdio调用，没有冒充已运行某款编辑器的自动review。
