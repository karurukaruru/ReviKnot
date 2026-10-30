# 可配置运行限制 / Configurable settings

以下默认值来自当前 0.6.1 源码。它们是应用侧限制，不代表模型或服务商的实际容量，也不是费用估算。

| 功能 | 默认值 | 参数或说明 |
|---|---:|---|
| 完整源码 review-source 上下文规划 | 100,000 | --context-tokens；按 UTF-8 字节保守估算，不是精确 tokenizer |
| review-source 单次回答上限 | 8,192 | --max-output-tokens；实际模型可能有更低限制 |
| review-source 最大分块数 | 20 | --max-chunks；超出时在发送请求前拒绝 |
| review-source 单文件大小上限 | 8 MB | --max-file-bytes；被跳过的文件会披露 |
| live 模型请求 / 工具轮数 / 修复提案 | 16 / 8 / 3 | --max-model-requests / --max-tool-turns / --max-repair-attempts |
| live 单次输出上限 | Nebius 2,048；其他默认 4,096 | --max-output-tokens；以所选模型实际能力为准 |
| live 单次请求预留 | 400,000 字节 | --token-reservation-limit；请求 UTF-8 字节加输出预留，不是 token 计费数 |
| live-demo 会话运行数 | 默认不限 | --max-runs N 可设置上限；每次运行仍由用户启动 |
| 新建持久请求账本 | 30 模型请求 / 10 搜索 / 5 模型发现 | --budget 指定账本；已有账本的限制和历史预留优先 |
| MCP 单个 JSON 输入文件 | 8,000,000 字节 | --max-file-bytes |
| MCP 每次比较返回的发现数 | 100 | --max-findings；总数和截断状态仍明确记录 |
| MCP 单个诊断字段预览 | 2,048 字符 | --max-finding-chars；原始长度和哈希仍保留 |

源码计划可以先免费检查，不调用模型：

    python -m reviknot review-source patchcourt --provider nebius --context-tokens 100000 --max-output-tokens 8192 --dry-run --output outputs/source-plan

真实 review-source 运行必须显式指定 --budget 持久账本。live 和 live-demo 的账本为可选项；若使用，已有记录不会被自动重置。预算调整需要明确指定新限制和原因，并保留审计记录。

提高输出上限可能增加响应时间和费用，也可能超过模型自身的限制。上下文规划值不是精确 token 数；模型实际支持范围需按服务商文档和实测确认。
