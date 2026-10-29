# 给编码Agent接入ReviKnot

适用时机：改了工具消息转换、升级SDK后，准备合并代码前检查一次。由宿主Agent按需调用，不需要定时轮询。

## 安装

解压源码，在项目目录用Python3.11或更新版本运行：

```powershell
python -m pip install -e ".[mcp]"
```

基础程序支持Python3.10；MCP额外依赖官方SDK，需要3.11+。安装不需要模型API密钥。

## 接到Codex

将下面两处路径换成实际绝对路径：第一个是刚安装环境的Python，第二个是要检查的工作区。

```powershell
codex mcp add reviknot -- D:/你的环境/Scripts/python.exe -m reviknot mcp --workspace D:/你的项目
```

如果路径带空格，用英文双引号包住。然后重新连接宿主MCP，查看是否出现ReviKnot的四个工具。
本轮已用官方SDK真实客户端跑通stdio；这里是宿主配置步骤，不冒称当前聊天已经自动接管编辑器。
[官方配置说明](https://developers.openai.com/codex/mcp/)。

## 让Agent何时调用

可以把这段话放入你自己项目的Agent工作说明：

> 修改工具消息序列化或升级SDK后，捕获相关适配器的原始输入和实际输出。调用ReviKnot检查，解释失败字段；修复后重新捕获、复验，并导出回归门禁。原版已经坏时，不能因为两个版本一样就判兼容。

捕获方法与完整示例在[英文技术说明](MCP.md)；只需在你明确选择的转换函数外围使用BoundaryRecorder，不会自动扫描执行整个项目。

| 工具 | 给它什么 | 得到什么 |
|---|---|---|
| inspect_boundary | 原输入JSON路径、实际输出JSON路径 | 具体语义变化位置 |
| check_recording | 一份BoundaryRecorder录制 | 该次转换是否保留原输入 |
| compare_recordings | 两份同适配器、同原输入的录制 | 基线与候选的契约状态；坏基线仍需检查 |
| export_regression_gate | 录制路径、新输出目录 | 可放进CI的Python标准库门禁 |

路径均相对配置的工作区。前三项只读；导出使用新目录，不覆盖旧证据。MCP本地检查不调用模型、不执行任意项目代码。
输出发现数、文件大小、诊断文字长度均可设置，详见[参数设置](OUTPUT_SETTINGS_ZH.md)。截断只影响诊断展示，保留标记、长度与哈希。

## 先免费试一下

```powershell
python examples/refund-agent/capture.py --output outputs/my-refund-case
python scripts/verify_mcp_workflow.py --output outputs/my-mcp-test
```

第二条使用装有MCP SDK的Python，真实启动stdio服务、调用四个工具并执行导出的门禁。
退款示例是本地受控数据：坏版本失败、保持原语义的版本通过、false改成0再次失败。没有真实客户、退款或支付。
新的NVIDIA生成修复是另一个显式live命令，才需要合法Nebius访问。
