# Platform feedback / 平台反馈

The model and provider results below are from the recorded 0.6.0 acceptance, included as execution evidence with the 0.6.1 source release.

Nebius Token Factory ran NVIDIA-Nemotron-3-Nano-30B-A3B for a bounded adapter repair and actual tool conversation: four calls, 5,992 reported tokens, eight checks, deliberately damaged mapping rejected and controlled inventory-value result 21. AI Cloud was not used or evaluated.

Useful: exact model discovery and returned identity, native tool calls, and original HTTP responses made the accepted run inspectable. A single repair proposal was enough in this final run. That is a small observed case, not a performance benchmark. MCP-based local verification then makes this result usable from a coding agent without paying for another model call per check.

Compatibility learning: our older strict client rejected empty annotations/audio/function_call metadata and a reasoning field. We fixed our adapter rather than attributing that rejection to the service. Per-model examples showing metadata, reasoning, tool turns, output/context limits and truncation behavior would make integration clearer. An earlier stop came from our own shared request ledger, not Nebius quota.

Onboarding: the user supplied access; authenticated model discovery and the OpenAI-compatible endpoint were exercised. Credit-email delivery and account signup latency were not measured. We did not test AI Cloud, throughput under load or a comparative cost claim.

I would use this stack again for controlled tool workflows with inspectable request history, while testing more independent tasks before wider deployment.

中文：确实使用了Token Factory和NVIDIA模型。首次兼容错误来自我们自己的字段白名单，旧预算中止来自我们自己的账本；没有据此指责平台。希望每型号文档更明确列出工具、reasoning、空字段、上下文和截断行为。AI Cloud没用过，开户与邮件耗时没测，不编造体验。MCP本地检查无需重复调用模型。
