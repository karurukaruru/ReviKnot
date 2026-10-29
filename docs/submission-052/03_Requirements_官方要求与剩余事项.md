# 官方要求与剩余事项 / Requirements and remaining work

核对日期 / Checked: **2026-10-26, Asia/Singapore**。当前为本地0.5.2准备材料；不是提交回执。登录后的必填字段和字数限制仍须由参赛者本人核对。

## 最先看这几句 / Read this first

官方要的是**公开源码仓库URL、可工作的演示/应用/测试版本URL、项目说明、公开视频链接和反馈**，没有指定必须上传一个总ZIP。ZIP是提供可下载测试版本的一种交付方式，不能替代公开源码仓库。Python可以用于本项目；没有必须改成EXE或某种前端框架的要求。[官方首页 / Overview](https://nebiusglobalaihackathon.devpost.com/)

Required delivery is link-based: a public source repository, working demo/app/test build, description, public video and feedback. A ZIP is a useful downloadable build, not a required universal submission format. Python is acceptable; the published requirements prescribe no EXE or frontend framework. [Overview](https://nebiusglobalaihackathon.devpost.com/)

比赛截止 **2026-10-31 01:00 SGT**；评委免费测试访问需保持到 **2026-12-16 04:00 SGT**。这些是官方Pacific时间转换到新加坡时间的结果。[官方规则 / Rules](https://nebiusglobalaihackathon.devpost.com/rules)

## 逐项交接 / Delivery checklist

| 事项 / Item | 实际要交什么 / Deliverable | 本轮状态 / Status | 后续动作 / Next action |
|---|---|---|---|
| 指定平台与模型 / Required runtime | NVIDIA开放模型在Nebius Token Factory运行时推理，或符合规则的Nebius AI Cloud执行 / Actual eligible execution | **缺访问，未完成 / Pending access** | 获得合法访问后跑产品完整流程，记录精确模型和实际结果 / Execute the product workflow and retain exact model/results |
| 程序与实测 / Product verification | 与说明一致的可运行功能、真实结果、失败记录 / Working behavior matching the entry | 0.5.2真实DeepSeek首次与复用PASS；单独评测PARTIAL已保留 / Initial/reuse live runs passed; separate evaluation retained as PARTIAL | 收尾复查；真Nebius后修复发现的问题，再验收 / Finish review; fix findings after actual Nebius integration |
| 测试版本链接 / Test-build URL | 可工作且评委免费可用的演示或测试包 / Functional free judge access | 本轮0.5.2本地测试包已验收；历史0.5.1已公开 / Local 0.5.2 accepted; older 0.5.1 public | 新包冻结、同意发布后验证匿名下载和启动；说明保存记录与新推理的区别 / Publish only with consent, verify download/launch, explain replay vs fresh inference |
| 公开源码 / Public source | GitHub/GitLab/Bitbucket、源码资源、可见开源许可证和README / Public repo, assets, visible license and setup | 本轮尚未上传 / Current iteration not uploaded | 最终版本审核后，由你决定何时授权同步 / Entrant authorizes final publication |
| 英文文案 / English copy | 功能、用途、技术角色、边界 / Features, audience, technology roles, limits | `01_Entry_English.md` + 简体中文审核稿已准备 / Prepared for review | 用真平台结果更新待测段落，适配实际字段长度 / Update only from executed evidence and actual form limits |
| 正式视频 / Final video | 小于3分钟为目标，实际运行画面，公开YouTube链接 / Aim below 3 minutes, functioning footage, public YouTube | **按你的要求暂停 / Paused by request** | 等你决定制作方式；现有开发样片不能冒充最终片 / Await entrant's production direction |
| 平台反馈 / Feedback | 对实际使用平台和模型的具体反馈 / Evidence-backed feedback | 保留工作草稿，未冒充最终反馈 / Draft only | Nebius实测后补事实；没用AI Cloud就如实写未使用 / Finalize after execution; disclose unused services |
| 既有工作披露 / Existing work | 比赛期间相对旧项目的重大改动 / Significant in-period additions | 源码 `COMPETITION_CHANGELOG.md` 已有 / Prepared | 纳入实际表单并核对署名/许可证 / Enter and verify attribution |
| 本人声明与提交 / Entrant declarations | 登录、资格、权利、团队及实际必填字段 / Login, eligibility, rights, team, required fields | 未替你声明或提交 / Not performed | 参赛者本人核对并提交，再保存成功状态 / Entrant confirms and submits |

指定平台条目依据[官方FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs)：通过Token Factory调用NVIDIA模型即可，前端无需也部署到Nebius；其他模型供应商不能替代这一条件。具体型号、额度、工具能力必须用账户实际可用情况验证。The frontend can stay elsewhere; another provider's call does not replace Nebius execution. [FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs)

表内交付条件按[官方规则](https://nebiusglobalaihackathon.devpost.com/rules)核对。表中的测试数量、完整产品验收、匿名下载复验、保存失败证据等是我们为可靠交付采用的工作标准，并非声称官方规定了某个请求数、测试数或ZIP结构。

## 视频：正式要求和官方建议分开 / Video: rules versus guidance

规则要求YouTube公开可见并在表单提供链接；建议少于三分钟，展示实际功能；未经许可不能使用他人商标、音乐等受保护材料。英文或提供英文翻译适用于提交材料。本项目不选Physical AI，其专属片段要求不套用到本项目。[Rules](https://nebiusglobalaihackathon.devpost.com/rules)

YouTube must be publicly visible and linked in the form. Keep the video below three minutes, show the working product, and use material you have permission to include. Provide English or an English translation. [Rules](https://nebiusglobalaihackathon.devpost.com/rules)

官方制作建议：文案、Built With和视频声音都明确点出Nebius及准确NVIDIA模型；视频先讲问题，再展示运行和用户价值。反馈需要具体说明用途、优点、改进点、上手过程，以及是否愿意再用及原因。这些应来自真实经历，不能提前代填成成功结果。[官方指南 / Official guidance](https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project)

The official guidance recommends naming the required technologies in the writeup, Built With and video audio, and giving specific feedback about actual use, strengths, weaknesses, onboarding and reuse. It is guidance for presentation and useful feedback, not permission to invent a successful run. [Official guidance](https://nebiusglobalaihackathon.devpost.com/updates/46205-how-to-build-a-winning-project)

## 到时需要你本人做什么 / What the entrant must do

1. Nebius可用后提供本地密钥文件的**路径**；是否充值、额度多少由你决定。不要把明文密钥放进公开材料。Provide only the local credential-file path when access is ready; funding is your decision.
2. 决定视频由谁制作、确认最终视频，再登录YouTube公开上传。Choose production ownership, approve the actual final cut, then publish it on YouTube.
3. 审核最终材料，决定是否允许同步本轮源码/测试包到公开仓库。Review and explicitly authorize any publication of this iteration.
4. 登录Devpost核对个人/团队资料、资格、第三方授权和许可证、所有实际必填字段，然后提交。Log in, verify personal/team information, eligibility, rights/licenses and required fields, then submit.

开发、测试、修复、双语稿、压缩包和核对材料可由开发侧继续完成；视频目前暂停，平台反馈等Nebius/NVIDIA实测后定稿。DeepSeek/Tavily开发实测已执行，不是所有API都没测。不会查看你的邮件、替你作个人声明或把本地文件夹当成已提交。DeepSeek/Tavily development execution is complete; Nebius/NVIDIA remains pending. Engineering can finish the materials, while video stays paused. Local delivery is not Devpost submission.
