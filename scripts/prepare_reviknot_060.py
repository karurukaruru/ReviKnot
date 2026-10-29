"""Prepare0.6.0 local evidence and bilingual entry copy; no network or publishing."""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]

def text(name,content):
    path=ROOT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(content.strip()+'\n',encoding='utf-8')

def main():
    from scripts.submission_check import verify_workflow,public_evidence
    live=ROOT/'outputs/submission-060/nebius-live-01'
    report,_=verify_workflow(ROOT,str((live/'report.json').relative_to(ROOT)),competition=True)
    proofroot=ROOT/'outputs/submission-060/mcp-workflow-03'
    proof=json.loads((proofroot/'mcp-workflow.json').read_text(encoding='utf-8'))
    assert proof['status']=='PASS' and proof['provider_requests']==0
    assert proof['execution']['mcp_server_source_sha256']==hashlib.sha256((ROOT/'patchcourt/mcp_server.py').read_bytes()).hexdigest()
    for name,checksum in proof['files'].items():
        path=(proofroot/name).resolve()
        assert path.is_relative_to(proofroot.resolve()) and hashlib.sha256(path.read_bytes()).hexdigest()==checksum
    for source,destination in ((live,ROOT/'evidence/nebius-060/live-01'),(proofroot,ROOT/'evidence/mcp-060')):
        for path in source.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':
                continue
            if path.suffix=='.json':
                public_evidence(json.loads(path.read_text(encoding='utf-8')))
            target=destination/path.relative_to(source)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    qa=ROOT/'evidence/review-060'
    qa.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'outputs/review-060/pytest-full.txt',qa/'pytest-full.txt')
    shutil.copyfile(ROOT/'outputs/review-060/pytest-final.txt',qa/'pytest-final.txt')
    shutil.copyfile(ROOT/'outputs/submission-050/budget.json',qa/'budget-snapshot.json')
    runtime='evidence/nebius-060/live-01/report.json'
    requests,tokens=len(report['requests']),report['total_reported_tokens']
    entry=f'''
# ReviKnot — Compatibility checks your coding agent can call

## The problem
A tool-using agent can break after an SDK or adapter change even when its tools
still run. Lost call IDs orphan the results; a valid JSON conversion can also
silently change nested arguments. Comparing two versions is insufficient when
both outputs already violate the original input.

## What ReviKnot does
ReviKnot checks captured messages against the original input contract and gives
the coding agent precise finding paths. Four local MCP tools inspect a boundary,
check a recording, compare recorded versions and export a portable regression
gate. Use it after editing message serialization or upgrading an SDK, before
proposing a merge. The host chooses when to invoke it; there is no continuous
polling or automatic editor trigger claimed.

The NVIDIA model workflow separately proposes a bounded declarative repair,
challenges it independently and runs the actual model/tool conversation. A
model cannot approve its own mapping. Python runs the checks, local interface,
isolated SDK workers and CLI. Credentials remain outside public artifacts.

## Actual execution
NVIDIA-Nemotron-3-Nano-30B-A3B ran on Nebius Token Factory in this0.6.0 acceptance:
{requests} model calls,{tokens} reported tokens,8 independent repair checks,
corrupted-repair rejection and a verified two-tool health check returning21
from local quantity3 and price7. The arithmetic is a diagnostic fixture, not
the product's main use case. Tavily retrieved supporting documentation.

The official MCP SDK2.3.0 client launched the real stdio server, discovered all
4 tools and made6 tool calls. A controlled refund-agent example includes two
tools, nested booleans, Unicode, currency and an approval requirement: lost IDs
FAIL, reviewed capture PASS, a false-to-zero mutation FAIL. Identical broken
captures remain NEEDS_REVIEW. The exported standard-library gate then runs in
isolated Python with expected broken/fixed/corrupt exits1/0/1. This uses local
synthetic data and never sends money. Actual installed NVIDIA SDK1.4.3/1.5.0
evidence is a separate credited historical case.

## Why use it
Keep the invariant that matters to your agent, inspect exactly what an adapter
changed, and retain a regression test that a later developer or CI can rerun.
MCP checks and exported gates require no model key or paid inference. They do
not import arbitrary project code. A coding host can call the same checker as
part of its existing edit/test workflow; host-specific setup instructions are
provided, while this release was integration-tested with the official client.

## Scope and next steps
This is scoped text/tool-message contract verification, not universal code
review or an arbitrary-code sandbox. Historical failed NVIDIA runs remain;
the earlier small developer-authored benchmark remains PARTIAL. No broad
accuracy, latency or cost advantage is claimed. Future work includes more
independent adapter cases and editor-host usability studies.

Built With: Python; NVIDIA Nemotron3 Nano30B A3B; Nebius Token Factory; Tavily;
Model Context Protocol; Remotion for the film.

Track: Coding and Agentic Engineering.
Repository: https://github.com/karurukaruru/agent-code-validator (publish0.6.0beforeentry).
Blog: https://karuru.top · X: https://x.com/djkaruru
'''
    zh=f'''
# ReviKnot — 编码Agent可以调用的兼容性检查

SDK或适配器改动后，工具可能仍能执行，但调用ID丢失会让返回结果接不上；有效JSON也可能把嵌套布尔值改成数字。两个版本输出一样，不等于它们保留了原输入。

ReviKnot对照原始输入检查捕获消息，返回具体字段位置。四个本地MCP工具分别检查消息边界、检查录制、比较录制版本、导出标准库回归门禁。适合在修改消息序列化或升级SDK后、准备合并前按需调用。由宿主Agent决定触发时机，没有声称每隔几秒后台监控或已经自动接管编辑器。

NVIDIA模型工作流负责提出受限声明式修复，由验证脚本检查，再运行真实模型/工具对话。最终0.6.0使用Nebius Token Factory上的NVIDIA-Nemotron-3-Nano-30B-A3B：{requests}次调用、{tokens}报告token、8项检查、破坏修复被拒、两工具健康检查得到21。3×7是通路诊断，不是产品主功能。

MCP已用官方SDK2.3.0的真实stdio客户端跑通：发现4个工具、调用6次。受控退款Agent包含两个工具、嵌套布尔、中文、币种及审批标志；丢ID的版本失败，保持原语义的版本通过，false改成0的版本失败。两个同样坏的版本仍是NEEDS_REVIEW。导出的独立门禁在隔离Python中呈现1/0/1退出码。示例不连接真实客户或支付；独立安装NVIDIA SDK的历史执行证据另列。

价值是保留Agent真正依赖的接口约束，并留下后续开发者和CI能复验的门禁。MCP检查不需要模型密钥、不调用付费API、不导入任意项目代码。提供编辑器接入说明；本轮真实集成验收用的是官方客户端，不冒充已录制Codex会话。

范围是审查过的文本/工具消息，不是万能代码审查或沙箱。旧失败记录与小型PARTIAL评测保留；不声称通用准确率或成本优势。后续可以扩展独立适配器案例与宿主使用体验。

参赛方向：Coding and Agentic Engineering。博客karuru.top；X@djkaruru。源码、测试版本与YouTube仍需发布，本人表单还未提交。
'''
    feedback=f'''
# Platform feedback / 平台反馈

Nebius Token Factory ran NVIDIA-Nemotron-3-Nano-30B-A3B for a bounded adapter
repair and actual tool conversation. Current0.6.0 result:{requests} calls,
{tokens} reported tokens,8 checks, deliberately damaged mapping rejected and
controlled inventory-value result21. AI Cloud was not used or evaluated.

Useful: exact model discovery and returned identity, native tool calls, and
original HTTP responses made the accepted run inspectable. A single repair
proposal was enough in this final run. That is a small observed case, not a
performance benchmark. MCP-based local verification then makes this result
usable from a coding agent without paying for another model call per check.

Compatibility learning: our older strict client rejected empty
annotations/audio/function_call metadata and a reasoning field. We fixed our
adapter rather than attributing that rejection to the service. Per-model
examples showing metadata, reasoning, tool turns, output/context limits and
truncation behavior would make integration clearer. An earlier stop came from
our own shared request ledger, not Nebius quota.

Onboarding: the user supplied access; authenticated model discovery and the
OpenAI-compatible endpoint were exercised. Credit-email delivery and account
signup latency were not measured. We did not test AI Cloud, throughput under
load or a comparative cost claim.

I would use this stack again for controlled tool workflows with inspectable
request history, while testing more independent tasks before wider deployment.

中文：确实使用了Token Factory和NVIDIA模型。首次兼容错误来自我们自己的字段白名单，旧预算中止来自我们自己的账本；没有据此指责平台。希望每型号文档更明确列出工具、reasoning、空字段、上下文和截断行为。AI Cloud没用过，开户与邮件耗时没测，不编造体验。MCP本地检查无需重复调用模型。
'''
    text('DEVPOST_SUBMISSION.md',entry)
    text('MOST_VALUABLE_FEEDBACK.md',feedback)
    for name,content in (('01_Entry_English.md',entry),('02_Entry_简体中文.md',zh),('03_Feedback_平台反馈_EN_ZH.md',feedback)):
        text('docs/submission-060/'+name,content)
    requirements='''
# 邮件逐项对照 / Submission checklist

依据用户2026-10-28贴出的提醒邮件，并复核公开规则；不是提交回执。

| 邮件事项 | 本地状态 | 仍需做什么 |
|---|---|---|
| Nebius运行并使用NVIDIA模型 | 0.6.0真实HTTP闭环PASS，原始证据在evidence/nebius-060 | 已完成技术验证 |
| 四个赛道选一 | Coding and Agentic Engineering | 本人表单选择 |
| 3分钟内、实际功能、说明Nebius/NVIDIA | 96秒无旁白英文画面版；准确平台/型号、英中字幕 | 看片确认后PUBLIC上传YouTube |
| 公开源码、可见开源许可、安装运行说明 | 完整源码、MIT、README、MCP接入说明已准备 | 公开本轮0.6.0并核对实际链接/commit |
| 可工作的demo URL | 免费评委测试包：录制回放、SDK检查、门禁；另含可安装MCP工具 | 发布实际测试版本下载URL并匿名复验；官方规则允许test build |
| 具体平台反馈 | 英文稿+中文对照，绑定真实运行 | 本人审核并填表 |
| 团队成员加入并接受邀请 | 未代填个人/团队资料 | 单人确认本人；组队逐个确认成员已接受邀请 |

提交截止：2026-10-31 01:00新加坡时间（邮件10月30日10:00AM PT）。
评审12月1–15日；免费访问保留到2026-12-16 04:00新加坡时间。
按收到的提醒邮件，截止前完成上传与最终冻结；截止后不改参赛仓库、视频或材料。
发布后记录源码commit、Release/test-build URL、公开视频URL及各文件SHA-256；
提交后保存回执。旧公开0.5.1不代表当前0.6.0。

无旁白是当前呈现选择，模型和平台以清楚的英文画面说明。官方展示指南建议声音点名；
规则要求英文或英文翻译，不要求全片持续解说。不能把静音片的spoken_attribution设成true。

Official rules: https://nebiusglobalaihackathon.devpost.com/rules
Presentation guidance: https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project
'''
    text('docs/submission-060/06_Checklist_邮件逐项对照.md',requirements)
    text('docs/submission-060/00_START_HERE_先看这里.md','''
# ReviKnot0.6.0 提交材料

01英文项目稿；02简体中文对照；03平台反馈；04评委测试；05表单备忘；06邮件逐项对照。
当前工程包括真实stdio MCP接口和NVIDIA/Nebius运行证据。没有上传或提交。
先看根目录FINAL_REMAINING_ZH.md；程序使用见MCP.md。
''')
    judge='''
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
'''
    text('JUDGE_TESTING.md',judge)
    text('docs/submission-060/04_Judge_Guide_评委使用说明.md',judge)
    text('docs/submission-060/05_Form_Fields_表单填写.md','''
# Form worksheet

Name: ReviKnot
Tagline: Compatibility checks your coding agent can call.
Track: Coding and Agentic Engineering.
Description:01_Entry_English.md; Chinese review:02_Entry_简体中文.md.
Feedback:03_Feedback_平台反馈_EN_ZH.md.
Built With: Python, MCP, NVIDIA Nemotron3 Nano30B A3B, Nebius Token Factory, Tavily.
Existing work: COMPETITION_CHANGELOG.md; historical SDK defects retain attribution.
Source: publish0.6.0to public repository and copy actualURL/commit.
Demo/test build: publish0.6.0Judge-Demo and test anonymous download/start.
Video: public YouTubeURL of actual96-second no-voiceEnglishdemo.
Team: add all actual teammates; confirm they accepted invitations.

Entrant confirms eligibility, ownership/licenses, team details and all login-only
required fields. Do not paste placeholders as actual links. Submit and save receipt
before2026-10-31 01:00Singapore; then freeze submitted repository/video/materials.
''')
    remaining='''
# 最后还需你做什么

程序、MCP真实调用、NVIDIA API和本地交付已经完成。MCP按需检查，没有声称后台自动审查一切。

1. 打开ReviKnot-Video-0.6.0/看片_Review.html确认最终无旁白视频，默认中英对照。
2. 发布本轮0.6.0公开源码和免费评委测试包；保留MIT许可证、README和MCP.md。核对实际commit与链接，并匿名下载/启动一次。
3. 把96秒英文画面演示PUBLIC上传YouTube，填实际公开视频URL；不要等最后才上传。
4. 登录Devpost选择Coding and Agentic Engineering，粘贴已准备的英文项目稿和反馈、源码URL、测试版本URL、YouTubeURL。
5. 核对本人/团队资格、权利和许可；组队确认成员都已加入并接受邀请。完成所有真实必填字段，正式提交并保存回执。
6. 按提醒邮件在截止前冻结源码commit、视频和材料；截止后不修改参赛版本。评审结束前保持测试访问免费可用。

截止2026-10-31 01:00新加坡时间；免费评审访问保留到2026-12-16 04:00。
邮件逐项对照见docs/submission-060/06_Checklist_邮件逐项对照.md。
本轮没有GitHub推送、YouTube上传、邮件操作、充值或Devpost提交；不能把本地交付当作已参赛。
'''
    text('FINAL_REMAINING_ZH.md',remaining)
    text('USER_ACTIONS_ZH.md',remaining)
    text('SUBMISSION_CHECKLIST.md',requirements)
    text('DEMO_SCRIPT.md','''
# ReviKnot0.6.0 demo story

96 seconds. Music and effects, with complete readable English on-screen
explanation and paired Chinese review captions. Show the silent message-boundary
problem, exact NVIDIA/Nebius execution, independently challenged repair, the
explicit3×7 controlled health check and actual MCP client/CI proof. Preserve
saved-evidence labels. A host initiates MCP checks after an adapter change;
no real editor session or background monitoring is invented. Finale names
the repository, karuru.top and X@djkaruru. Spoken attribution is false for
this cut; reviewed English visual platform/model attribution is explicit.
''')
    text('CURRENT_CHECKPOINT_ZH.md',f'''
# ReviKnot0.6.0 current checkpoint

2026-10-28，新加坡时间。本文件取代旧停止点，旧交付保留。
新增正式stdio MCP四工具，官方SDK2.3.0客户端六次调用通过；退款示例与独立门禁1/0/1。
最终完整回归701通过、4个Windows权限跳过、201子测试通过，日志evidence/review-060/pytest-final.txt。
新NVIDIA/Nebius0.6.0闭环PASS：{requests}请求/{tokens}报告token/8检查/破坏负控拒绝/21。
继续旧账本；用户授权必要实测后显式上限64，当前40模型/9搜索/1目录，旧消耗和审计保留。
视频保持96秒设计，改无旁白英文画面说明、中文对照、真实MCP价值与博客karuru.top。
没有推送、发布、邮箱操作或充值。剩余本人步骤见FINAL_REMAINING_ZH.md。
''')
    manifest=json.loads((ROOT/'submission-manifest.json').read_text(encoding='utf-8'))
    manifest.update(project='ReviKnot — Compatibility checks your coding agent can call',runtime_workflow=runtime,
        feedback_review='evidence/review-060/feedback-review.json',video=None,
        note='Local0.6.0: actual NVIDIA workflow and official-client MCP integration verified. Current source/testbuild/YouTube not published and entrant form not submitted. No-voicevideo uses reviewedEnglishvisualattribution.')
    text('submission-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    review={'reviewed_at':datetime.now(timezone.utc).isoformat(),'document_sha256':hashlib.sha256((ROOT/'MOST_VALUABLE_FEEDBACK.md').read_bytes()).hexdigest(),
        'runtime_report_sha256':hashlib.sha256((ROOT/runtime).read_bytes()).hexdigest(),'observations_backed_by_records':True,
        'scope':'Technical observations checked against original records; entrant reviews final subjective feedback and form.'}
    text('evidence/review-060/feedback-review.json',json.dumps(review,indent=2))
    for name in ('README.md','README.zh-CN.md'):
        previous=ROOT/'docs/history'/('README_053_'+('EN.md' if name=='README.md' else 'ZH.md'))
        previous.parent.mkdir(parents=True,exist_ok=True)
        if not previous.exists():
            shutil.copyfile(ROOT/name,previous)
    text('README.md',f'''
# ReviKnot

**Compatibility checks your coding agent can call before an SDK change reaches production.**

Local version 0.6.0. [简体中文](README.zh-CN.md) · [MCP setup](MCP.md) · [Executed evidence](RELEASE_REVIEW_060_ZH.md) · [Submission actions](FINAL_REMAINING_ZH.md)

An adapter can silently lose tool-call IDs or change nested arguments while its
output is still valid JSON. ReviKnot checks the captured output against the
original input contract. Even identical outputs do not establish compatibility
when both were already broken.

## Use it in your coding workflow

Capture the affected message boundary after changing an adapter or upgrading
an SDK. Your coding agent can call four local MCP tools to inspect it, compare
recordings and export a standalone regression gate. Failures identify field
paths. Check the repaired capture again and keep the gate in CI.

From an extracted source checkout, Python 3.11+:

```sh
python -m pip install -e ".[mcp]"
python -m reviknot mcp --workspace .
```

The server waits on stdio for its host. [MCP.md](MCP.md) provides the actual
Codex registration command and tool arguments. No global editor configuration
is changed silently. The host chooses when to invoke checks; this release does
not claim continuous background monitoring or a recorded editor session.

## Try it without any model key

```sh
python -m reviknot demo --output outputs/my-demo
python -m reviknot serve outputs/my-demo
python examples/refund-agent/capture.py --output outputs/my-refund-case
```

The demo records controlled cases and intentionally retains failures. The
refund example has two tool calls, nested booleans, Unicode, currency and an
approval requirement. Lost IDs FAIL, preserved input PASS, false-to-zero
mutation FAIL. It is synthetic local data; no customer or payment system runs.
The base CLI supports Python 3.10+; optional MCP uses Python 3.11+.

## NVIDIA repair workflow

An explicitly selected NVIDIA model proposes a bounded declarative mapping.
Independent checks and a deliberately damaged mapping challenge it before the
actual tool conversation is allowed to succeed. Arbitrary model Python is not
executed. Keep credentials in an ignored local `.env.local`:

```sh
python -m reviknot --env-file .env.local live --provider nebius --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B --budget outputs/my-budget.json --output outputs/my-new-live-run
```

This command makes paid provider requests. MCP checks, saved replay and
exported gates do not. Request/output/context limits are configurable;
[OUTPUT_SETTINGS_ZH.md](OUTPUT_SETTINGS_ZH.md) explains their scope and audit
trail. [Full source review](SOURCE_REVIEW.md) is a separate chunked workflow.

## What was actually executed

-0.6.0 NVIDIA Nemotron on Nebius Token Factory: {requests} model calls, {tokens}
reported tokens, 8 checks, corrupted repair rejected, controlled health check 21.
-Official MCP SDK 2.3.0 client → stdio: 4 tools, 6 calls; independent exported gate
exits 1/0/1 for broken/fixed/corrupt captures. [Original MCP evidence](evidence/mcp-060/mcp-workflow.json).
-Real installed NVIDIA SDK 1.4.3/1.5.0 workers are a separate credited historical
case. Equal broken outputs remain NEEDS_REVIEW. [SDK execution](UPGRADE_RUN.md).
-Current tests and release checks are recorded in [RELEASE_REVIEW_060_ZH.md](RELEASE_REVIEW_060_ZH.md).

The checker covers reviewed text/tool-message schemas, not every SDK or
arbitrary project code. Redacted/unsupported captures do not earn PASS. Hashes
detect changes but do not authenticate a producer. Historical failures and the
small developer-authored PARTIAL benchmark remain available; no universal
accuracy or comparative performance claim is made.

## Development and judging

```sh
python -m pip install pytest pytest-subtests
python -m pytest
```

The free judge portal and standard-library gates require no model account.
Fresh MCP use needs its optional SDK; fresh NVIDIA generation needs lawful API
access. See [JUDGE_TESTING.md](JUDGE_TESTING.md). This iteration is local, not yet
published or submitted. [MIT license](LICENSE); credited source and third-party
notices remain with their evidence. Legacy `patchcourt` and `acv` entry points
are retained for compatibility; the product name is ReviKnot.

Repository: https://github.com/karurukaruru/agent-code-validator
Blog: https://karuru.top · X: https://x.com/djkaruru
'''.replace('\n-0.6','\n- 0.6').replace('\n-Official','\n- Official').replace('\n-Real','\n- Real').replace('\n-Current','\n- Current'))
    text('README.zh-CN.md',f'''
# ReviKnot

**给编码Agent使用的兼容性检查：在SDK改动合并前，发现消息字段被静默改坏。**

当前本地版本0.6.0。MCP接口已实现并实测；本轮没有推送、发布或提交。
[MCP接入](MCP.md) · [开发复查](RELEASE_REVIEW_060_ZH.md) · [最后本人操作](FINAL_REMAINING_ZH.md)

## 什么情况下用

修改工具消息序列化、升级SDK后，捕获这段适配器的真实输入和输出。让编码Agent调用ReviKnot，
检查调用ID、名称、参数与结果关系是否保留，查看具体失败路径，修改后重新捕获复验，最后导出门禁放进CI。
两个版本都产生相同坏输出，仍不能判兼容。

## 先接到Agent

解压源码后，在项目目录使用Python3.11+：

```sh
python -m pip install -e ".[mcp]"
python -m reviknot mcp --workspace .
```

第二条启动stdio服务，等待宿主连接，不会打开网页。Codex注册命令和四个工具参数见[MCP.md](MCP.md)。
不会偷偷修改全局编辑器配置；由宿主Agent在相关修改后或合并前触发，不需要每隔几秒轮询。
MCP不调用模型、不加载.env、不执行任意项目代码，检查和导出门禁不产生模型费用。

## 无需API先体验

```sh
python -m reviknot demo --output outputs/my-demo
python -m reviknot serve outputs/my-demo
python examples/refund-agent/capture.py --output outputs/my-refund-case
```

基础CLI支持Python3.10+。演示保留故意失败的对照，并非每格都应该绿。
退款例子包含两个工具、嵌套布尔、中文、币种与审批要求：丢ID失败，保持原语义通过，false改成0失败。
这是本地受控示例，不连接客户或支付；检查的是消息是否保真，不是替你审核退款业务规则。

## NVIDIA模型负责什么

通过Nebius Token Factory提出受限字段映射，由独立脚本检查，再运行真实模型/工具对话。
不执行模型任意Python。0.6.0真实运行：{requests}次请求、{tokens}报告token、8项检查通过、故意破坏修复被拒、健康检查结果21。
3×7只是确认工具链能完成的诊断值，不是产品主功能。

新推理才需要ignored `.env.local`中的合法NEBIUS_API_KEY与准确模型ID；
见[NEBIUS_RUNBOOK_ZH.md](NEBIUS_RUNBOOK_ZH.md)。输出、调用数、上下文、MCP诊断长度均可配置；
见[OUTPUT_SETTINGS_ZH.md](OUTPUT_SETTINGS_ZH.md)。长源码全文读取/分块压缩是单独的[review-source](SOURCE_REVIEW.md)。

## 验收与范围

官方MCP SDK2.3.0客户端真实启动stdio子进程，发现4工具、调用6次；导出门禁在隔离Python中得到1/0/1。
真实已安装NVIDIA SDK1.4.3/1.5.0的历史执行证据另列，不冒充新缺陷。
测试日志与最终校验见[0.6.0复查](RELEASE_REVIEW_060_ZH.md)。
目前支持已审查的文本/工具消息，不是万能代码审查或沙箱；不支持、已脱敏或不完整记录不能判PASS。
哈希用于发现改动，不认证提交者。旧失败与PARTIAL评测保留，不编造通用准确率或获奖保证。

MIT许可证与历史源码署名保留；旧patchcourt/acv入口兼容。
博客https://karuru.top；Xhttps://x.com/djkaruru；仓库https://github.com/karurukaruru/agent-code-validator。
当前免费评委测试包与96秒无旁白视频使用见[JUDGE_TESTING.md](JUDGE_TESTING.md)。
''')
    print(json.dumps({'status':'PASS','runtime':runtime,'model_requests':requests,'reported_tokens':tokens,'mcp_calls':len(proof['workflow']),'published':False}))

if __name__=='__main__':
    main()
