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
不执行模型任意Python。0.6.0真实运行：4次请求、5992报告token、8项检查通过、故意破坏修复被拒、健康检查结果21。
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
博客https://karuru.top；Xhttps://x.com/djkaruru；仓库https://github.com/karurukaruru/ReviKnot。
当前免费评委测试包与96秒无旁白视频使用见[JUDGE_TESTING.md](JUDGE_TESTING.md)。
