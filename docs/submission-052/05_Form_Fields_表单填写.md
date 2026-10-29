# 表单填写与链接核对 / Form and link worksheet

**这是待核对工作表，不是表单提交回执。** Devpost登录后的准确字段、长度、复选框和团队资料未被本地文档验证。没有占位URL或编造的个人声明可以关闭这些事项。

This worksheet does not assert the exact authenticated form schema or its limits. Copy only verified values into the corresponding fields after the entrant logs in.

## 可以直接审阅的文字 / Text ready for review

| 用途 / Purpose | 文件 / File | 使用方式 / Use |
|---|---|---|
| 项目英文介绍 / English description | `01_Entry_English.md` | 审阅正文；真Nebius完成后替换待测段落 / Review now; update the pending paragraph only after execution |
| 中文对照 / Chinese translation | `02_Entry_简体中文.md` | 供你看懂英文稿，最终提交保留英文 / Use for review; retain English in the entry |
| 测试说明 / Testing instructions | `04_Judge_Guide_评委使用说明.md` | 英文部分给评委；核对最终包实际启动器 / Use English with the final tested package |
| 平台反馈 / Platform feedback | 源码根目录 `MOST_VALUABLE_FEEDBACK.md` | 当前是草稿，等真Nebius后定稿 / Evidence-led draft; finalize after actual Nebius execution |
| 既有项目变化 / Existing-work disclosure | 源码根目录 `COMPETITION_CHANGELOG.md` | 披露ACV基线和比赛期间新增，不声称历史问题为新发现 / Disclose baseline and additions; credit known defects |

## 必须按真实情况填的值 / Values that must be real

| 字段 / Field | 当前事实 / Current fact | 关闭条件 / Completion condition |
|---|---|---|
| Project name | PatchCourt — AI Agent Compatibility Guardian | 本人接受命名 / Entrant approves |
| Track | Coding and Agentic Engineering | 实际表单选中对应赛道 / Select the actual form option |
| Built With / model | 0.5.2 DeepSeek首次/复用PASS、Tavily已真实检索，单独评测PARTIAL；Nebius/NVIDIA待测 / Current initial/reuse live runs pass, evaluation PARTIAL; target inference pending | 用报告中的精确NVIDIA模型ID和实际角色更新，不掩盖部分结果 / Exact executed model and role; retain partial results |
| Final source URL | 本轮0.5.2未上传 / Current 0.5.2 not published | 获准发布后填写最终公开commit URL并匿名复验 / Authorized publication and anonymous verification |
| Demo/test-build URL | 本轮0.5.2本地测试包已验收，尚未公开 / Current local test build accepted; not published | 上传获准后核对最终包、启动和免费评审访问 / Authorized final build and free judge access verified |
| YouTube URL | 暂无最终正式公开视频 / No final public competition video | 本人确认最终片、设为Public并匿名打开 / Approved final cut, Public, checked logged out |
| Feedback | 未完成最终Nebius/NVIDIA观察 / Final target observations pending | 实测完成，内容与记录一致 / Executed, reviewed findings |
| Team/representative | 不预填身份 / Not assumed | 本人填写真实成员、代表权限 / Entrant verifies members/authority |
| Eligibility | 不替你确认 / Not declared for you | 本人阅读规则，确认年龄、居住地及适用限制 / Entrant reviews and confirms |
| Ownership and permissions | 代码含上游开源组件和保留许可证 / Upstream components and licenses retained | 本人确认新贡献权利和上游/媒体使用授权 / Entrant confirms contribution rights and third-party/media permissions |
| Submission status | 尚未提交 / Not submitted | 实际提交成功页面或状态；保留项目URL / Actual success status and project URL |

## 最后一次核对 / Final review

1. 文案、Built With、视频、源码和实际运行的模型/版本一致。The writeup, Built With, video, source and executed model/version agree.
2. 最终源码含LICENSE、README、运行资源和说明；文档链接可用。Final source contains the license, README, resources and working references.
3. 下载最终测试包，在干净目录启动；回放、离线控制和实际云端证据清楚区分。Launch the final downloaded build in a clean folder; distinguish playback, offline controls and actual cloud evidence.
4. 评委测试到评审结束前免费可用；不要让评委为了查看演示去买额度。Judge testing remains free through the judging period; do not require credit purchases to inspect the intended demonstration.
5. 视频公开可见，英文可理解，第三方素材有权使用。The video is public, understandable in English and uses authorized materials.
6. 反馈保留失败和限制，不把预期错误响应当平台缺陷；没有使用的服务写明未使用。Feedback retains failures/limits and distinguishes expected errors; disclose unused services.
7. 本地检查器仍报告缺项时，先看具体原因，不能把缺项字段改成true来“通过”。If the local checker reports a missing gate, inspect the reason; never fabricate booleans or evidence.

源码目录可运行以下检查；它不联网，也不代表Devpost已接收作品：

```bash
python scripts/submission_check.py --output outputs/submission-readiness.json
```

退出码2表示缺少证据；1表示已提供的证据有错或不一致；0只表示本地记录满足检查，可交本人复核。Exit 2 means missing evidence; 1 means supplied evidence fails validation; 0 means ready for entrant review, never automatic acceptance by Devpost.

入口：[Devpost submissions](https://devpost.com/submit-to/30790-nebius-x-nvidia-global-ai-hackathon/manage/submissions)、[官方规则 / Rules](https://nebiusglobalaihackathon.devpost.com/rules)、[YouTube Studio](https://studio.youtube.com/)。
