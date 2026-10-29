# Quick start / 快速开始

1. Download the **Source.zip** from [the latest release](https://github.com/karurukaruru/ReviKnot/releases/latest), extract the whole folder, install Python 3.11+, and open a terminal there. / 下载完整源码包，全部解压，准备 Python 3.11+，在该目录打开终端。
2. Run the command below. It creates the environment, installs every runtime tool, checks real MCP discovery, generates configuration and opens the local example. / 一个命令完成环境、全部工具、真实连接检查、配置和网页启动。

```sh
python setup_reviknot.py --open
```

Open http://127.0.0.1:8765/ if the browser does not open. Ctrl+C stops the server. First installation downloads packages; use `python3` on macOS/Linux if needed. / 浏览器没自动打开就访问该地址；按 Ctrl+C 停止。首次安装需要联网。

Expected: broken adapter FAIL, preserved input PASS, corrupted repair FAIL. No model key needed. / 错误版本 FAIL，正确版本 PASS，损坏修复 FAIL，不用模型密钥。

## Connect your agent / 接入 Agent

Pick your client; all four tools are configured together. / 选择客户端，四个工具一次配置。

```sh
python setup_reviknot.py --client codex
```

Replace `codex` with `cursor` or `claude-code` as needed. Add `--workspace /absolute/project/path` to use another project. Codex needs its CLI; generic client configurations are generated under `.reviknot/` even without it. Existing unrelated client settings are preserved. Restart/reload the client and allow the project MCP. / 可换为其他客户端或指定项目；完成后重新加载客户端，按提示允许 MCP。

Ask your agent: “After this adapter change, check the captured boundary with ReviKnot, explain failed fields and export a regression gate.” / 可以说：“改完适配器后，用 ReviKnot 检查消息边界，解释失败字段，并导出回归测试。” [Tool arguments / 工具参数](MCP.md) · [中文捕获示例](MCP.zh-CN.md)

## Confirm / 检查

```sh
python run_reviknot.py doctor
```

Expect `status: PASS` and four discovered tools: `check_recording`, `compare_recordings`, `export_regression_gate`, `inspect_boundary`. This opens a real MCP stdio connection and makes no provider requests. / 真实发现四个工具，不调用模型 API。

## Fresh inference / 自己的模型

Copy `.env.example` to ignored `.env.local`; uncomment the fields you use and set `NEBIUS_API_KEY` and an available NVIDIA Nemotron `NEBIUS_MODEL`. / 填自己的密钥和可用模型 ID。

```sh
python run_reviknot.py --env-file .env.local live --provider nebius --output outputs/my-live-run
```

Only this explicit inference flow spends provider credits. Use a new output folder for each report. / 该项才会调用付费 API；每次使用新的输出目录。

## Troubleshooting / 常见问题

| Symptom / 现象 | Action / 处理 |
|---|---|
| Python missing | Install Python 3.11+; try `python3` or Windows `py -3.12`. |
| MCP missing | Rerun `python setup_reviknot.py`; MCP is included by default. |
| Codex CLI missing | Use the generated `.reviknot/codex.toml`, or rerun after installing the CLI. |
| Tools not visible | Restart/reload the client, allow the project MCP, run `doctor`. |
| Bare `mcp` command waits | It serves stdio; use `setup_reviknot.py --open` for a web page. |
| Existing output directory | Pick a new output path; previous evidence is preserved. |
| Download failure | Correct package-index/network access and rerun; the environment is reused. |
| Port occupied | Stop the previous server or use `python run_reviknot.py serve .reviknot/demo --port 8766`. |

Advanced install: `python -m pip install -e .`, then `python -m reviknot setup`. All runtime tools are included without an extra install. Python 3.10 supports legacy CLI only. / 自己管理环境时，也默认一次装齐全部运行依赖。
