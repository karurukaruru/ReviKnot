# Development evaluation findings / 开发评估结果

**Status: PARTIAL. This is a recorded DeepSeek development experiment, not a successful Nebius/NVIDIA qualification run.**

**状态：PARTIAL（部分完成）。这是实际 DeepSeek 开发实验，不代表已通过 Nebius/NVIDIA 比赛平台验收。**

Evidence: `evidence/development-052/deepseek-evaluation-01/`. The plan, benchmark, all six inference responses, retrieval response and integrity manifest remain available. No response was retried or replaced to improve the reported result.

证据在 `evidence/development-052/deepseek-evaluation-01/`。保留了事先保存的方案、结果、六次推理回复、检索回复与完整性清单，没有为了美化结果重试或替换某次结果。

## What ran / 实际执行了什么

- Requested and returned model: `deepseek-flash`, via the DeepSeek API. All six calls returned HTTP 200 and the expected model identity.
- Twelve developer-authored protocol examples, repeated unchanged in two trials. These are 12 distinct examples, not 24 independent examples, and are not an independent held-out or blind test.
- Five arms: deterministic comparison (A), the original ACV code-review prompt/parser (B), bounded model classification (C), the same classification with Tavily documentation (D), and exact-repeat reuse with fresh deterministic verification (E).
- Six inference calls reported **19,324 total tokens**, including the truncated response. One shared Tavily basic search reported **one credit**. Dollar cost is unknown; reported tokens and search credits are separate measures.

中文：请求和返回的模型都是 `deepseek-flash`，六次请求的 HTTP 与模型身份检查均通过。12 个开发者编写的协议样例原样重复两轮，不能称为 24 个独立样例，也不是独立盲测。五组分别为确定性比较、原 ACV 审查、模型分类、模型加官方文档检索、精确记录复用后重新比较。六次模型调用共报告 **19,324 tokens**，另有一次 Tavily basic 检索，报告 **1 credit**；没有据此编造美元费用。

| Arm / 组别 | Executed rows / 已执行样例行 | Exact labels / 与预设标签一致 | Important qualification / 解释 |
| --- | ---: | ---: | --- |
| A — deterministic / 确定性比较 | 24/24 | 24/24 | Implements this declared local contract / 实现本地预设契约 |
| B — original ACV / 原 ACV | 12/24 | 5/12 executed | Second response truncated; 12 rows are ERROR / 第二轮截断，12 行 ERROR |
| C — model / 模型分类 | 24/24 | 18/24 | Three recurring mismatches per trial / 每轮相同三类偏差 |
| D — model + Tavily / 模型加检索 | 24/24 | 18/24 | Same labels as C on every paired row / 与 C 每一对标签都相同 |
| E — reuse + verification / 复用并复验 | 24/24 | 24/24 | Same comparator as A; 8/12 knowledge hits per trial / 与 A 同一比较器，每轮命中 8/12 |

The table measures agreement with the frozen local labels, including correct abstention/review labels. It is not a general model leaderboard. In particular, B performs code review rather than C/D's classification task; a bug finding for the exact input filename maps to FAIL, while other B outcomes abstain. A numerical B-versus-C ranking would hide that task difference.

这张表统计与冻结标签是否一致，包括正确输出“不确定”或“需复核”，不能包装成通用模型排行榜。尤其 B 执行代码审查，C/D 执行特定分类：B 对对应文件提出 bug 才映射为 FAIL，其他情况按弃权处理；直接据此宣称谁总体更强是不公平的。

## Why the experiment is PARTIAL / 为什么不是完整通过

The only arm execution error is **trial 2, B-original-ACV**:

- `trial-2-B-original-ACV.json` records HTTP 200, assistant role, the requested model identity, `finish_reason: "length"`, and **2,048 completion tokens**, exactly the configured output cap.
- The reply ends inside an unfinished JSON string (`file` on line 104). It cannot be accepted as a complete review.
- The response validator correctly records `Incomplete model response`; all 12 rows for that arm/trial remain ERROR/unexecuted. They are not counted as successful classifications. The failed request and token usage remain counted.
- This is **output truncation under the chosen experiment budget**, not a refusal, HTTP failure, model identity mismatch or demonstrated provider defect. Trial 1 B ended normally but already used 2,044 completion tokens, showing the review format was close to the same cap.

唯一的执行错误是**第二轮 B-original-ACV**：HTTP 成功，但模型输出到达设置的 2,048-token 上限，`finish_reason` 为 `length`，JSON 在 `file` 字符串处截断。验证器正确拒收，12 行保留为 ERROR，没有当作通过；请求和消耗仍计入统计。第一轮 B 已使用 2,044 输出 tokens，也非常接近上限。因此这是当前预算与长审查格式不匹配导致的截断，不能说是模型拒答、网络故障或平台缺陷。

The low-level request records say PASS because the HTTP response decoded successfully. The benchmark's separate completion validation and `arm_errors` determine whether the response was usable. **HTTP PASS is not experiment PASS.** No program crash or silent acceptance of the truncated reply was found in this run.

底层请求记录的 PASS 表示 HTTP 返回可解析；是否能用，还必须看回复完整性与 `arm_errors`。**HTTP 成功不等于实验通过。**本次没有发现程序崩溃，也没有把截断回复偷偷当作有效结果。

## What the complete model arms got wrong / 完整返回的模型仍错在哪里

C and D both produced complete, schema-valid replies with `finish_reason: "stop"`. They had the same three mismatches in each trial:

| Case / 样例 | Frozen label / 预设标签 | C and D / 实际标签 | Interpretation / 含义 |
| --- | --- | --- | --- |
| `unlinked-baseline-result` | NEEDS_REVIEW | PASS | Identical traces still contain an orphan tool result in the baseline; equality does not make the starting transcript valid. / 两份内容相同，但起始记录本身缺少对应工具调用，仍应复核。 |
| `adjacent-text-segments` | PASS | FAIL | Human/user role normalization and concatenated text are equivalent under this comparator. / 按本比较器规则，human/user 别名与相邻文本拼接可等价。 |
| `normalized-call-representation` | PASS | INCONCLUSIVE | LangChain's ai/normalized-tool-call representation is supported by this comparator. / 本比较器支持 ai 别名与 LangChain 归一化工具调用。 |

There is an important **prompt specification limitation**: the frozen classification prompt explicitly covers text concatenation, empty content, image defaults and invalid baseline linkage, but does **not explicitly enumerate** `human → user`, `ai → assistant`, or the flattened LangChain tool-call field mapping used by the comparator and expected labels. The last two errors therefore also expose an underspecified evaluation prompt; they cannot be attributed solely to a model's general reasoning ability. The invalid-baseline check was explicitly requested, and both model arms still missed it.

这里存在一个必须披露的**提示词说明不足**：冻结提示词明确写了文本拼接、空内容、图片默认值、无效起始关联，但没有逐项写出 `human → user`、`ai → assistant` 和 LangChain 扁平工具调用的字段映射，而比较器与标签支持这些规则。因此后两项偏差也反映测评提示词没有讲全，不能全部归因于模型推理能力。起始记录关联检查已经明确要求，模型两组仍遗漏了这一项。

This observation does not change the frozen run. Any expanded classification contract needs a separately versioned plan and new evidence; the existing labels, prompt, raw responses and scores must stay intact. The subsequent offline v2 protocol correction is described below; it does not change the v1 evidence.

这个发现不会改写本轮冻结记录。补充分类契约应使用新版本方案、单独记录结果；不能修改旧提示词、原始回复或分数来补成“全过”。下文说明随后完成的离线 v2 协议修正；它没有改变 v1 实测证据。

## What the results support / 可以据实说明什么

- **Independent checking remains necessary.** The recorded model proposals are not accepted as final truth; the deterministic verifier can reject unsupported or invalid evidence rather than trusting fluent model explanations.
- **No retrieval accuracy gain was observed here.** All 24 paired C/D labels were identical; every recorded correctness delta was zero. D supplied documentation and produced a citation on one row per trial, but citation presence is not evidence of improved correctness.
- **E is verified reuse, not a new reasoning improvement.** E had eight knowledge hits per 12 rows in each trial and reran the same deterministic comparator on hits and misses. Some records were created from C in the same trial, and their creation cost is already in C's calls. E's 24/24 label agreement and zero additional inference calls cannot establish generalization or a measured end-to-end token-saving ratio.
- **A/E agreeing with all local labels does not prove production completeness.** The corpus and implementation come from the same development process. Wider user traces, independent examples and actual Nebius/NVIDIA runtime behavior remain outside this experiment.

中文：可以据实说明“模型建议必须经过独立核验”。不能说检索提高了准确率：C/D 的 24 对标签完全相同；带引用也不等于更正确。E 每轮只是 8/12 精确命中，命中与未命中都会运行同一个比较器；有些记录还是同轮从 C 创建，前置成本已经发生。因此不能把 E 的结果说成未见样例推理更强，或宣称已经测得整个流程的节费比例。A/E 与开发者标签全部一致，也不能证明生产环境无遗漏，更不能替代 Nebius/NVIDIA 真实接入验收。

## Evidence pointers / 查证文件

- Plan and limits / 事先方案与限制：`plan.json`
- Aggregate, per-trial rows, paired retrieval and errors / 汇总、逐轮、检索对比与错误：`benchmark.json`
- Truncated response / 截断原文：`trial-2-B-original-ACV.json`
- Complete baseline response / 第一轮完整审查：`trial-1-B-original-ACV.json`
- Model-only responses / 不带检索：`trial-1-C-model.json`, `trial-2-C-model.json`
- Model-with-documentation responses / 带检索：`trial-1-D-model-Tavily.json`, `trial-2-D-model-Tavily.json`
- Shared documentation / 共享检索：`retrieval.json`
- Integrity / 完整性：`manifest.json`

All pointers above are relative to `evidence/development-052/deepseek-evaluation-01/`. Hashes support file integrity, not independent authentication of the provider's provenance. No Nebius/NVIDIA API was used in this experiment.

以上路径均相对于 `evidence/development-052/deepseek-evaluation-01/`。哈希用于核对文件完整性，不是第三方对平台来源的独立认证。本实验没有调用 Nebius/NVIDIA API。

## Offline v2 protocol correction / 已完成的离线 v2 协议修正

The current evaluation code now uses **`patchcourt-release-evaluation-v2`, protocol `2.0`**. It explicitly states role/type handling and human/user, ai/assistant aliases; OpenAI and flattened LangChain tool-call equivalence; parsed object arguments and supported legacy fields; content/image normalization; and baseline validation before comparison. These are general rules matching the existing deterministic comparator, without per-case answer labels.

当前评估代码已改用 **`patchcourt-release-evaluation-v2`、协议 `2.0`**：明确说明 role/type 与 human/user、ai/assistant 别名，OpenAI 和 LangChain 扁平工具调用的等价映射，参数对象解析与兼容字段，文本/图片归一化，以及先验证起始记录再比较的顺序。这些是与现有比较器一致的通用规则，没有向模型提供各样例答案。

The original v1 prompt remains in code as `CONTRACT_V1`, with its recorded contract hash `8fbbc469f26eb39aec66300ed57f4073e0d4fb3a676d95950fdd7b004489bcaa`. The new plan identifies its previous protocol/hash and uses a new opaque-ID namespace. The twelve cases, literal labels and corpus hash remain unchanged. The plan is written before retrieval or inference. Tests check this ordering, unchanged plan bytes, version provenance and that model requests exclude case names and expected labels.

旧提示词保留为 `CONTRACT_V1`，哈希与旧记录一致。新方案写明 v1 来源及哈希，使用新的不透明 ID 命名空间。12 个样例、预设标签和语料哈希均未改变。方案先落盘，再检索或推理；离线测试验证这个顺序、方案内容不被中途改写、版本追溯，以及请求中不夹带样例名称和答案标签。

**v2 has only offline/synthetic-transport verification so far. No real model performance has been measured for v2.** The v1 18/24 scores above cannot be relabeled as v2 scores, and this prompt correction does not establish a gain or resolve B's previously observed output-cap risk. Any future real v2 run must use a fresh output directory and stay within the existing request budget.

**v2 目前只完成离线与模拟传输验证，没有真实模型成绩。**上面的 v1 18/24 不能改名为 v2 成绩；补全规则也不代表已测得提升，原 ACV 长回复达到输出上限的风险仍须保留。将来真实验证 v2 必须使用新目录，并遵守已有请求预算。

The current general reasoning/evaluation output default has also been raised to **8,192 tokens**, with an explicit setting up to **65,536** for DeepSeek/Nebius. The selected budget is frozen in each new evaluation plan and sent unchanged; it is an application ceiling, not a verified claim about the selected Nebius model. This gives future runs more room without relabeling the old 2,048-token experiment. Replies ending with `length` still fail validation; there is no automatic retry. Short live/lab fixtures retain their existing explicit budgets.

当前通用诊断/评估的默认输出也提高到 **8,192 tokens**，DeepSeek/Nebius 可显式设置到 **65,536**。新评估方案会事先记录实际选择的额度，并原样发送，不静默压回小上限；65,536 是应用上限，不代表已验证某个 Nebius 模型支持。这个调整为未来运行留出更多空间，没有改写旧的 2,048-token 实验。`length` 截断仍判失败，不自动重试；短 live/lab 演示保留原有明确预算。
