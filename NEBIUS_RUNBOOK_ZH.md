# ReviKnot0.6.0 · Nebius运行与可调限制

0.6.0真实目标模型已完成闭环：`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`，官方Token Factory端点，4次模型请求、5992报告token、8项检查、负控拒绝、工具结果21。证据见evidence/nebius-060。另一次完整源码审查已完成20613字符覆盖，前次TLS失败与后次成功分别保留；模型建议不等于已验证缺陷。没有把其他供应商结果替代NVIDIA实测，也未测AI Cloud部署。

凭据只放ignored `.env.local`，使用NEBIUS_API_KEY/NEBIUS_MODEL；不上传。后续运行使用新output目录，并继续同一个账本保留历史消耗。失败HTTP尝试也占次数；次数不是美元保证。模型/搜索/目录请求分别记账。

用户已批准按必要用途使用已有额度，旧账本模型上限有审计地30→36→64，当前40/64、搜索9/10、目录1/5。`python -m reviknot budget outputs/submission-050/budget.json --model-calls 80 --reason "my next experiment"`可以显式调整上限，并保留旧记录和审计；不是自动重置。也可设置--searches、--discovery-calls，具体以`budget --help`为准。不要并发运行超出实际账户余额的实验。

```powershell
python -m reviknot --env-file .env.local live --provider nebius --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B --budget outputs/submission-050/budget.json --max-model-requests 16 --max-tool-turns 8 --max-repair-attempts 3 --max-output-tokens 4096 --output outputs/my-next-run
```

默认live模型/工具轮数/提案上限16/8/3；输出默认2048，可改。输出上限65536是应用范围，不保证该型号支持。长源码review-source默认上下文100000，完整分块后压缩发现，不因单次输出2048就只读取2048源码。详见OUTPUT_SETTINGS_ZH.md与SOURCE_REVIEW.md。

回放、录制、打包不需要再调用API。只有真实新推理才用账户；不会充值、查看邮件或自动发布。
