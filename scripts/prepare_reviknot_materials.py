"""Freeze local ReviKnot submission copy from executed evidence; no network."""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

def write(name, text):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip() + "\n", encoding="utf-8")

def main():
    from scripts.submission_check import verify_workflow, public_evidence
    run = ROOT / "outputs/submission-050/nebius-053-20261027/live-03"
    report, records = verify_workflow(ROOT, str((run / "report.json").relative_to(ROOT)), competition=True)
    assert report["status"] == "PASS" and len(report["requests"]) == 4
    for name in ("discovery.json",):
        source = run.parent / name
        public_evidence(json.loads(source.read_text(encoding="utf-8")))
        target = ROOT / "evidence/nebius-053" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in ("live-01", "live-02", "live-03"):
        source, dest = run.parent / name, ROOT / "evidence/nebius-053" / name
        dest.mkdir(parents=True, exist_ok=True)
        for path in source.iterdir():
            if path.is_file() and path.suffix in {".json", ".md", ".html"}:
                if path.suffix == ".json":
                    public_evidence(json.loads(path.read_text(encoding="utf-8")))
                shutil.copyfile(path, dest / path.name)
    for name in ("pytest-053-final.txt", "pytest-053-final-export.txt", "wheel-qa.json"):
        source = ROOT / "outputs/review-053" / name
        dest = ROOT / "evidence/review-053" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    write("evidence/nebius-053/README.md", """
# ReviKnot 0.5.3 · real Nebius/NVIDIA evidence

Final `live-03/report.json`: PASS, NVIDIA-Nemotron-3-Nano-30B-A3B on Nebius Token Factory. Four actual model requests, 5631 reported tokens. Eight independent repair checks pass, the corrupted repair is rejected, and the actual model/tool conversation recovers 3×7=21. These are controlled local tools, not a commercial inventory integration. The repair executes an audited historical adapter snapshot with inert message types; separate installed-SDK evidence covers releases1.4.3/1.5.0.

`live-01` preserves the old metadata-envelope rejection and an independently invalid candidate. `live-02` preserves the later global-budget stop after verification/tool execution; it is INCONCLUSIVE. Neither is rewritten into a success. `live-03` is a new complete run. HTTP sidecars, canonical hashes and exact requested/returned models are retained. Saved replay sends no inference requests; checksums detect changes and are not third-party attestations.
""")
    write("CURRENT_CHECKPOINT_ZH.md", """
# ReviKnot 当前检查点 / Current checkpoint

2026-10-28，新加坡时间。本文件取代旧停止点；历史开发记录见各版本RELEASE_REVIEW。

项目正式名称 **ReviKnot**，本地版本0.5.3；旧Python导入名patchcourt/acv兼容保留。外部代码审查六项已逐项处理；初轮完整回归616通过、4个Windows权限跳过。最终补充导出器一致性修复的验证以RELEASE_REVIEW_053_ZH.md为准。

真实Nebius NVIDIA Nemotron闭环已PASS：4次模型请求、5631报告token、8项独立检查、破坏负控拒绝、实际工具结果21。成功与前两次失败/中止记录一起保存在evidence/nebius-053；不能只留下好结果。

继续同一outputs/submission-050/budget.json；用户已明确批准模型上限30→36，保存审计与旧使用记录，当前34/36模型、8/10搜索、1/5目录请求。没有充值。次数、工具轮数、修订次数和输出长度可自设，见OUTPUT_SETTINGS_ZH.md。

视频已恢复制作，当前96秒ReviKnot版本使用该次真NVIDIA记录更新画面及旁白。原GLM草稿保留。不得把历史草稿当目标平台最终版。当前视频/源码交付以外层ReviKnot目录和验收记录为准。

本轮没有GitHub推送、YouTube上传、邮件操作或Devpost提交。剩余人工步骤见FINAL_REMAINING_ZH.md。
""")
    write("FINAL_REMAINING_ZH.md", """
# 最后还要做什么 / Remaining actions

**程序与真实NVIDIA API验证已经完成；API不再是缺项。** 本地包与视频不代表已经参赛提交。当前版本ReviKnot0.5.3；本轮没有向GitHub上传。

1. **看片**：打开ReviKnot视频目录的`看片_Review.html`，可看中文对照；确认最终声音、画面与署名。
2. **发布本轮源码和测试包**：把ReviKnot0.5.3源码、许可证、README和Judge-Demo ZIP放到公开仓库/Release。旧仓库URL仍可沿用，但旧0.5.1发布不代表当前版本。发布后做一次匿名下载/解压/启动检查；保存准确commit和链接。
3. **YouTube**：公开上传最终96秒英文演示，填实际视频URL；`unlisted`不等于规则要求的公开。文案在docs/submission-053。
4. **Devpost**：登录、选择Coding and Agentic Engineering，粘贴英文项目说明、Built With、平台反馈、源码URL、免费测试包URL和YouTube URL；核对个人/团队、资格、授权、许可证与实际必填字段，点击提交并保存回执。
5. **维持免费评审访问**：评审期结束前保留可下载/可运行测试版本。离线回放和SDK/门禁验证不需要评委API密钥；新推理须使用合法账户，不共享私人密钥。

英文稿、简体中文对照、反馈、评委说明、表单备忘均已整理。登录后的字段限制与个人声明仍需本人确认。没有用软件替你作资格或权利声明，也没有伪造发布/提交记录。

Official requirements: https://nebiusglobalaihackathon.devpost.com/rules
Deadline: 2026-10-31 01:00 Singapore; free judging access through2026-12-16 04:00 Singapore. Checked2026-10-28.
""")
    write("USER_ACTIONS_ZH.md", "# 你要做的事\n\n请直接看 [最后清单](FINAL_REMAINING_ZH.md)。API已实测通过；剩下看片、公开源码/免费测试包、YouTube上传与Devpost本人提交。当前本地开发结果不能冒充公开发布。")
    write("NEBIUS_RUNBOOK_ZH.md", """
# ReviKnot · Nebius运行与可调限制

0.5.3真实目标模型已完成闭环：`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`，官方Token Factory端点，8项检查、负控拒绝、工具结果21。证据见evidence/nebius-053。没有把其他供应商结果替代NVIDIA实测，也未测AI Cloud部署。

凭据只放ignored `.env.local`，使用NEBIUS_API_KEY/NEBIUS_MODEL；不上传。后续运行使用新output目录，并继续同一个账本保留历史消耗。失败HTTP尝试也占次数；次数不是美元保证。模型/搜索/目录请求分别记账。

用户已批准旧账本模型上限30→36，当前34/36、搜索8/10、目录1/5。`python -m reviknot budget outputs/submission-050/budget.json --model-calls 48 --reason "my next experiment"`可以显式调整上限，并保留旧记录和审计；不是自动重置。也可设置--searches、--discovery-calls，具体以`budget --help`为准。不要并发运行超出实际账户余额的实验。

```powershell
python -m reviknot --env-file .env.local live --provider nebius --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B --budget outputs/submission-050/budget.json --max-model-requests 16 --max-tool-turns 8 --max-repair-attempts 3 --max-output-tokens 4096 --output outputs/my-next-run
```

默认live模型/工具轮数/提案上限16/8/3；输出默认2048，可改。输出上限65536是应用范围，不保证该型号支持。长源码review-source默认上下文100000，完整分块后压缩发现，不因单次输出2048就只读取2048源码。详见OUTPUT_SETTINGS_ZH.md与SOURCE_REVIEW.md。

回放、录制、打包不需要再调用API。只有真实新推理才用账户；不会充值、查看邮件或自动发布。
""")
    write("OUTPUT_SETTINGS_ZH.md", """
# 限制可以自己改 / Configurable settings

| 设置 | 默认 | 自定义 |
|---|---:|---|
| 全源码review-source上下文规划 | 100000 | --context-tokens |
| review-source / reason / evaluation输出 | 8192 | --max-output-tokens，最高65536（GLM8192） |
| live单次输出 | 2048 | --max-output-tokens，最高65536 |
| live模型请求 / 工具轮数 / 提案次数 | 16 / 8 / 3 | --max-model-requests / --max-tool-turns / --max-repair-attempts |
| live-demo会话运行数 | 3 | --max-runs |
| live请求字节及输出预留总量 | 400000 | --token-reservation-limit（保守预算，非实际计费token） |
| 同一持久账本总调用数 | 初始模型30 / 搜索10 / 目录5 | reviknot budget显式调整并写审计 |

```powershell
python -m reviknot budget outputs/submission-050/budget.json --model-calls 48 --reason "increase for my next experiment"
python -m reviknot review-source patchcourt --provider nebius --context-tokens 100000 --max-output-tokens 16384 --dry-run --output outputs/my-source-plan
```

第二条免费检查分块计划；实际运行再提供凭据与账本，去掉--dry-run。源码读取的完整范围和哈希保留，全部分块有效才称COMPLETE；跨块汇总压缩结构化发现，不承诺把10万源码原样塞进每次请求。

上下文规划按请求UTF-8字节数保守估算，并非精确tokenizer。输出是上限，不是必须写满的长度。模型实际支持范围可能更小；截断/拒绝会保留失败。增大输出会占用上下文、延长响应并提高费用。所有操作参数在运行报告中保存。预算调整不充值，不清零消耗。
""")
    en = """
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
"""
    zh = """
# ReviKnot — 在接口边界拦住AI Agent的静默回归

Agent工具明明执行成功，下一轮却坏了：SDK适配器丢掉工具调用ID。两个版本都输出同样的坏结果，普通差异比较还可能误判正常。

ReviKnot对照原始输入语义检查消息，调用NVIDIA模型提出有界字段映射，独立挑战修复，再运行真实模型和工具对话。模型不能自行宣布修复成功；被拒提案和失败运行都保留。用户也能捕获自己的接口边界，导出不需要API的Python回归门禁。

Python实现CLI、本地浏览器界面、语义检查和隔离SDK执行。Nebius Token Factory实际运行NVIDIA-Nemotron-3-Nano-30B-A3B，负责修复提案和工具对话；Tavily提供文档检索。只执行声明式映射，不执行任意模型Python。复用绑定源码、环境和验证器身份。长源码全读后分块压缩发现；输出和运行次数可配置。

最终目标平台运行用了4次模型请求、5631报告token：8项检查通过，故意破坏的修复被拒，两个本地受控工具返回数量3、单价7，真实模型输出21。另有实际安装SDK1.4.3/1.5.0的执行证据：两个版本都坏时仍是NEEDS_REVIEW。CI门禁对坏版本/破坏修复失败，对审查后修复通过。

已修复JSON恢复、异常停止、并行动作拒绝、已读取源码证据、请求统计和流式ID等问题。前两次NVIDIA失败/中止保留。这不是任意代码沙箱，不代表所有SDK版本都有问题；旧缺陷有出处。小规模自编样例评测保留PARTIAL，不宣称通用准确率或检索提升。

后续可扩展独立SDK样例和用户捕获场景。目前已有免费回放测试包、源码、wheel、回归门禁与96秒演示。真正提交前还要公开发布本轮0.5.3、上传YouTube并完成本人表单。
"""
    write("DEVPOST_SUBMISSION.md", en)
    write("docs/submission-053/01_Entry_English.md", en)
    write("docs/submission-053/02_Entry_简体中文.md", zh)
    feedback = """
# ReviKnot · Evidence-backed platform feedback

**Use.** Nebius Token Factory ran NVIDIA-Nemotron-3-Nano-30B-A3B to propose a declarative adapter repair and perform the repaired tool conversation. The successful run used4 model calls,5631 reported tokens,8 independent checks and returned21 from two controlled local tools. AI Cloud was not used or evaluated.

**Worked well.** Authenticated model discovery exposed the exact NVIDIA model identity. Native tool calls supported the inventory/price flow; original responses preserved matching requested/returned model names and stop reasons. One initial proposal was sufficient in the final run. These observations cover a small controlled case, not a general benchmark.

**Needs work / developer opportunity.** The chat endpoint included empty annotations/audio/function_call fields and a separate reasoning string. Our restrictive adapter initially rejected these, so we fixed our client; we do not classify that as a service failure. Provider-specific schema examples covering null metadata, reasoning, tool calls and completion limits would reduce compatibility surprises. Clear per-model output/context/tool-capability information near quickstart examples would help developers choose settings. Earlier budget exhaustion came from our own request ledger, not Nebius quota.

**Onboarding.** We used the user-provided credential file, authenticated model discovery, and the OpenAI-compatible endpoint. No account-creation timing or credit-email delivery time was measured, so neither is asserted here.

**Would use again.** Yes for bounded tool workflows where original HTTP evidence and model identity can be retained. Before broader deployment we would test larger independent tasks, latency distributions, failure recovery and actual costs; no comparative speed/cost claim is supported by this run.

简体中文：Token Factory与NVIDIA Nemotron已实际用于修复及工具闭环；8项检查、负控、21结果有原始记录。首次错误来自我们的字段白名单，另一次中止来自我们自己的账本，不甩锅平台。希望文档更清楚列出各模型工具、reasoning、空字段和输出限制。AI Cloud未使用；未测开户/邮件耗时；愿再用，但不以单次小任务声称普遍性能优势。
"""
    write("MOST_VALUABLE_FEEDBACK.md", feedback)
    write("docs/submission-053/03_Feedback_平台反馈_EN_ZH.md", feedback)
    write("docs/submission-053/04_Judge_Guide_评委使用说明.md", """
# ReviKnot · Judge testing / 评委测试

Download and extract ReviKnot-Judge-Demo-0.5.3.zip. Python3.10+ is sufficient; no pip install, account, API key or payment is needed for saved replay and regression gates. Windows: double-click Start-Judge-Demo.cmd. Other platforms: run python launch_demo.py. Open the printed loopback URL.

1. Inspect the saved NVIDIA repair:8 checks, corrupted repair rejected, task result21. Playback is explicitly recorded, not a new inference call.
2. Open installed-SDK comparison: equal broken outputs do not pass compatibility.
3. Inspect the included ci-gate and run its standard-library unittest instructions. Broken and corrupted fixtures intentionally fail; reviewed repair passes.
4. Read original HTTP sidecars/source attribution. All traces use controlled local tools and an audited historical adapter snapshot; installed-release results are a separate evidence set.

For fresh inference install the included wheel and use your own lawful Nebius credentials and a named budget. Do not enter private keys into the static replay. The source README explains current commands and configurable limits.

中文：解压测试包后双击启动即可；保存记录的回放、SDK对比和回归门禁不需要API。新模型调用才使用合法账户。真实记录与新推理分开标注。评审访问应免费保留到评审结束。
""")
    write("JUDGE_TESTING.md", (ROOT / "docs/submission-053/04_Judge_Guide_评委使用说明.md").read_text(encoding="utf-8"))
    write("docs/submission-053/05_Form_Fields_表单填写.md", """
# 表单填写 / Form worksheet

Project name: ReviKnot
Tagline: Stop silent agent regressions at the boundary.
Track: Coding and Agentic Engineering.
Description: 01_Entry_English.md; Chinese review:02_Entry_简体中文.md.
Built With: Python, NVIDIA Nemotron3 Nano30B A3B, Nebius Token Factory, Tavily, HTML/CSS/JavaScript.
Feedback:03_Feedback_平台反馈_EN_ZH.md.
Existing work: COMPETITION_CHANGELOG.md and source attribution; do not claim discovery of historical SDK bugs.
Source URL: existing repository may be reused AFTER publishing this iteration.
Test-build URL: actual public release URL of ReviKnot-Judge-Demo-0.5.3.zip.
YouTube URL: actual PUBLIC upload of final96-second movie.

Login-only field limits, personal/team identity, eligibility and rights must be checked by the entrant. Do not paste placeholders as real links. Submit and save the receipt before2026-10-31 01:00 Singapore.
""")
    write("docs/submission-053/00_START_HERE_先看这里.md", """
# ReviKnot0.5.3 提交材料

01英文项目稿；02中文对照；03平台反馈；04评委测试；05表单备忘。程序、真实NVIDIA验证和本地材料已完成；公开发布、YouTube上传和本人提交仍待执行。

官方规则：https://nebiusglobalaihackathon.devpost.com/rules
官方展示建议：https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project
核对2026-10-28。要求公开源码、可工作测试版本URL、说明、公开视频URL和平台反馈；ZIP是我们的测试版本载体，Python不需改成EXE。视频96秒，英文配简体中文审核稿。详细本人动作见根目录FINAL_REMAINING_ZH.md。
""")
    write("SUBMISSION_CHECKLIST.md", "# Submission checklist\n\nCurrent ReviKnot0.5.3 engineering and real NVIDIA validation are complete. See FINAL_REMAINING_ZH.md for publication, YouTube and entrant form actions. scripts/submission_check.py deliberately keeps missing public/form records BLOCKED; it does not manufacture submission completion. Current English/Chinese material: docs/submission-053/. Historical evidence and earlier public releases are preserved separately.")
    write("DEMO_SCRIPT.md", "# ReviKnot96-second demonstration\n\nThe film shows a silent boundary failure, a bounded NVIDIA model proposal, eight independent checks, a rejected corrupted repair, actual controlled tools and result21, inspectable evidence, capture-to-CI workflow and final repository/X. It uses the final real Nebius/NVIDIA record. The editorial workflow diagram is labeled separately from captured execution. English subtitles and a Chinese viewing companion are delivered beside the movie; original reference voices and rights notices remain attributed.")
    feedback_path = ROOT / "evidence/review-053/feedback-review.json"
    runtime = "evidence/nebius-053/live-03/report.json"
    review = {"reviewed_at":datetime.now(timezone.utc).isoformat(), "document_sha256":hashlib.sha256((ROOT/"MOST_VALUABLE_FEEDBACK.md").read_bytes()).hexdigest(), "runtime_report_sha256":hashlib.sha256((ROOT/runtime).read_bytes()).hexdigest(), "observations_backed_by_records":True, "scope":"Technical evidence review; entrant must approve personal subjective feedback and actual form."}
    feedback_path.write_text(json.dumps(review, indent=2)+"\n",encoding="utf-8")
    manifest = json.loads((ROOT/"submission-manifest.json").read_text(encoding="utf-8"))
    manifest.update(project="ReviKnot — AI Agent Compatibility Guardian", runtime_workflow=runtime, feedback_review="evidence/review-053/feedback-review.json", note="Local0.5.3: NVIDIA workflow and feedback technical review complete. Current source/test build and YouTube not published; entrant form not submitted. Historical artifacts remain historical.")
    write("submission-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    for filename in ("README.md", "README.zh-CN.md"):
        path = ROOT/filename
        text = path.read_text(encoding="utf-8")
        start = text.find("**Current iteration:")
        if start >= 0:
            end = text.find("\n\n",start)
            text = text[:start]+"**Current iteration: local ReviKnot0.5.3.** Real NVIDIA Nemotron inference on Nebius Token Factory passed the complete repair/tool workflow:8 independent checks, corrupted-repair rejection, result21,4 model calls and5631 reported tokens. Current evidence: [NVIDIA run](evidence/nebius-053/README.md). Runtime limits are configurable with audited persistent budget changes. Current source/test-build publication, YouTube and entrant submission remain pending. [Final review](RELEASE_REVIEW_053_ZH.md)."+text[end:]
        oldstart=text.find("**Development status — competition submission is still pending.**")
        if oldstart>=0:
            end=text.find("\n\n",oldstart)
            text=text[:oldstart]+"**Competition status:** the actual NVIDIA/Nebius workflow is now verified in [0.5.3 evidence](evidence/nebius-053/README.md). Earlier DeepSeek/GLM runs and published0.5.1 remain historical. This local version has not been pushed or submitted."+text[end:]
        path.write_text(text,encoding="utf-8")
    print(json.dumps({"status":"PASS","runtime":runtime,"model_requests":4,"reported_tokens":5631,"published":False}))

if __name__ == "__main__":
    main()
