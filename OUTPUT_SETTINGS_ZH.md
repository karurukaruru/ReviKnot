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
| MCP每个JSON输入文件 | 8000000字节 | --max-file-bytes |
| MCP每项比较的发现数 | 100 | --max-findings，保留总数和截断标记 |
| MCP单个诊断字段 | 2048字符 | --max-finding-chars，截断保留长度与哈希 |

```powershell
python -m reviknot budget outputs/submission-050/budget.json --model-calls 48 --reason "increase for my next experiment"
python -m reviknot review-source patchcourt --provider nebius --context-tokens 100000 --max-output-tokens 16384 --dry-run --output outputs/my-source-plan
```

第二条免费检查分块计划；实际运行再提供凭据与账本，去掉--dry-run。源码读取的完整范围和哈希保留，全部分块有效才称COMPLETE；跨块汇总压缩结构化发现，不承诺把10万源码原样塞进每次请求。

上下文规划按请求UTF-8字节数保守估算，并非精确tokenizer。输出是上限，不是必须写满的长度。模型实际支持范围可能更小；截断/拒绝会保留失败。增大输出会占用上下文、延长响应并提高费用。所有操作参数在运行报告中保存。预算调整不充值，不清零消耗。
