# ReviKnot

**JSON 合法，Agent 也可能坏掉。先检查消息语义有没有丢，再发布 SDK 或适配器变更。**

[English](README.md) · [快速开始](QUICKSTART.md) · [MCP 接入](MCP.zh-CN.md) · [96秒演示](https://github.com/karurukaruru/ReviKnot/releases/download/v0.6.0/ReviKnot-96s-Demo.mp4)

ReviKnot 检查工具调用 ID、嵌套参数等内容是否被完整保留，返回具体出错位置，并导出能运行的回归测试。两个输出一样，也可能是两个都错了；检查依据是原始输入契约。

这里公开的是 **MIT 许可的完整程序**，包含 MCP、命令行、网页、源码审查、模型工作流和回归导出。无需解锁功能。评委小包是方便试看的保存记录；[最新 Release](https://github.com/karurukaruru/ReviKnot/releases/latest)同时提供完整源码和安装包。

## 第一次用：一个命令跑起来

准备 **Python 3.11 或更新版本**。下载并解压完整源码，在项目目录打开终端：

```sh
python setup_reviknot.py --open
```

它会自动创建环境、一次安装全部运行依赖（含 MCP）、用真实连接发现四个工具、生成接入配置，并打开 **http://127.0.0.1:8765/**。不用 API。首次安装需要联网下载依赖；按 Ctrl+C 停止网页。macOS/Linux 可以用 `python3`。

预期结果：错误适配器 FAIL，正确保留输入的版本 PASS，故意损坏的修复 FAIL。负控显示 FAIL 是正常结果。

## 接到 Agent：选客户端，一次配好

| 客户端 | 命令 | 自动处理 |
|---|---|---|
| 已安装 CLI 的 Codex | `python setup_reviknot.py --client codex` | 用检查过的 Python 路径注册 MCP。 |
| Cursor | `python setup_reviknot.py --client cursor` | 合并当前项目的 `.cursor/mcp.json`。 |
| Claude Code | `python setup_reviknot.py --client claude-code` | 合并当前项目的 `.mcp.json`。 |
| 其他 MCP 客户端 | `python setup_reviknot.py` | 生成 `.reviknot/mcp.json` 和 `codex.toml`。 |

后面可以加 `--workspace 你的项目绝对路径` 接到另一个项目。原来其他 MCP 服务的配置会保留，发生修改的配置会备份。完成后重启或重新加载客户端，按提示允许项目 MCP，即可发现全部四个工具，不用逐个安装。

可以对 Agent 说：

> 改完适配器后捕获输入输出，用 ReviKnot 检查原始输入有没有被完整保留，解释出错字段，修复后再检查，最后导出回归测试。

工具负责直接检查消息、检查录制事务、比较两份录制、导出回归门禁。[接入文档](MCP.zh-CN.md)提供参数和捕获方法，由客户端按任务调用即可，不需要每隔几秒轮询。

## 之后怎么运行

不用手动激活环境，统一用这个入口：

```sh
python run_reviknot.py doctor
python run_reviknot.py --help
python run_reviknot.py review-source . --dry-run --output outputs/source-plan
```

`doctor` 实际连接 MCP 并检查全部依赖。最后一条只规划完整源码审查，不调用模型。每次报告使用新的输出目录。

已有 Python 环境，也可以运行 `python -m pip install -e .`，默认包含全部运行工具，再运行 `python -m reviknot setup --client codex`。不再需要单装 MCP；旧的 `[mcp]` 写法仍兼容。Python 3.10 保留基础命令兼容；完整功能使用 3.11+。

## 接自己的模型

把 `.env.example` 复制为 `.env.local`，去掉 Nebius 两行前面的 `#`，填自己的 `NEBIUS_API_KEY` 和明确的 `NEBIUS_MODEL`（未使用的服务保持注释）：

```sh
python run_reviknot.py --env-file .env.local live --provider nebius --output outputs/my-live-run
```

这一项会实际调用 API。本地检查、MCP、保存记录播放和导出门禁不需要模型账号。Nebius、DeepSeek、GLM 工作流均包含；配置 Tavily 密钥后可以加 `--tavily`。

网页默认允许不限次数的手动运行，需要时设 `--max-runs N`。每次运行的请求数、轮数、输出长度和可选账本都能配置。源码审查默认按 10万 token 规划，并按需拆分、压缩。模型实际容量由服务商决定。[设置说明](OUTPUT_SETTINGS_ZH.md)。

## 验证与边界

- Nebius 上 NVIDIA Nemotron 的真实记录：4次调用、5,992个报告 token、8项检查和损坏修复负控。
- 官方 MCP 客户端调用全部四个工具，错误／修复／损坏门禁退出码分别为1／0／1。
- 保留真实安装 SDK 的比较记录、源码归属与历史失败。视频展示0.6.0验收，0.6.1改善安装接入，没有冒充新一轮模型实测。

MCP 检查录制的消息契约；完整源码审查是单独的模型工作流。项目不会因两个错误输出一样就判通过，也不会自动执行模型返回的 Python。

[MIT许可](LICENSE) · [架构](ARCHITECTURE.md) · [评委说明](JUDGE_TESTING.md)

GitHub：https://github.com/karurukaruru/ReviKnot · 博客：https://karuru.top · X：https://x.com/djkaruru
