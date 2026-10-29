# ReviKnot · Evidence-backed platform feedback

**Use.** Nebius Token Factory ran NVIDIA-Nemotron-3-Nano-30B-A3B to propose a declarative adapter repair and perform the repaired tool conversation. The successful run used4 model calls,5631 reported tokens,8 independent checks and returned21 from two controlled local tools. AI Cloud was not used or evaluated.

**Worked well.** Authenticated model discovery exposed the exact NVIDIA model identity. Native tool calls supported the inventory/price flow; original responses preserved matching requested/returned model names and stop reasons. One initial proposal was sufficient in the final run. These observations cover a small controlled case, not a general benchmark.

**Needs work / developer opportunity.** The chat endpoint included empty annotations/audio/function_call fields and a separate reasoning string. Our restrictive adapter initially rejected these, so we fixed our client; we do not classify that as a service failure. Provider-specific schema examples covering null metadata, reasoning, tool calls and completion limits would reduce compatibility surprises. Clear per-model output/context/tool-capability information near quickstart examples would help developers choose settings. Earlier budget exhaustion came from our own request ledger, not Nebius quota.

**Onboarding.** We used the user-provided credential file, authenticated model discovery, and the OpenAI-compatible endpoint. No account-creation timing or credit-email delivery time was measured, so neither is asserted here.

**Would use again.** Yes for bounded tool workflows where original HTTP evidence and model identity can be retained. Before broader deployment we would test larger independent tasks, latency distributions, failure recovery and actual costs; no comparative speed/cost claim is supported by this run.

简体中文：Token Factory与NVIDIA Nemotron已实际用于修复及工具闭环；8项检查、负控、21结果有原始记录。首次错误来自我们的字段白名单，另一次中止来自我们自己的账本，不甩锅平台。希望文档更清楚列出各模型工具、reasoning、空字段和输出限制。AI Cloud未使用；未测开户/邮件耗时；愿再用，但不以单次小任务声称普遍性能优势。
