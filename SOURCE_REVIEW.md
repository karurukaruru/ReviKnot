# Full scanned-source review / 完整读取已扫描源码

`patchcourt review-source` plans every scanned source fragment before calling a
model. It does not apply the older diagnostic's 16,000-character source slice or
the classic ACV review's 30,000-character per-file truncation. Source files are
read as data and are never imported or executed.

新增全文审查会先给全部扫描到的源码分块，再逐块送审，不会只取文件开头。
默认上下文预算为 **100,000**，默认回答上限为 **8,192**，输入窗口和回答长度
分别设置。DeepSeek/Nebius 的应用可配置输出上限为 **65,536**；这不是对尚未
实测的 Nebius 模型能力作保证，也不会强制模型写满这个长度。

## Plan without an API / 免费查看完整计划

From the source checkout, with Python 3.10+:

```powershell
python -m patchcourt review-source patchcourt --provider deepseek --context-tokens 100000 --max-output-tokens 8192 --dry-run --output outputs/source-plan
```

Use a new output directory for every run. A dry run needs no credential or model
discovery. `PLANNED` means the input plan exists; it does not mean code was
reviewed. Inspect `plan.json`, `report.json` and each `chunks/*-input.json` before
authorizing a real run. Plans may contain source text; share them only if that
source is suitable for sharing.

`--dry-run` 不调用模型、不搜索、不需要密钥。先看分块数和覆盖范围，避免为了
“全读”无意发出大量请求。每次使用新的输出目录，原报告不会被覆盖。

## Run a budgeted review / 在明确预算内实测

```powershell
python -m patchcourt --env-file .env.local review-source patchcourt --provider deepseek --context-tokens 100000 --max-output-tokens 8192 --budget outputs/submission-050/budget.json --output outputs/source-review
```

The CLI requires a persistent request ledger for a real run. It checks that the
whole plan fits the remaining request count before sending its first request.
Reservations remain in the ledger if a later call fails. It neither resets the
ledger nor retries automatically. Concurrent consumption can still exhaust a
previously sufficient budget; the report then retains unfinished coverage.

真实执行必须指定共享账本。默认最多20块，超过时在发请求前停止；可用
`--max-chunks` 显式调整，但不会替你提高账本次数上限。参数
`--max-output-tokens` 可以提高回答上限；更长输出可能增加时间和费用。
模型返回输出截断时，该块明确记为未完成。

For Nebius, use an exact NVIDIA Nemotron model available to the account. The
planner makes no automatic discovery call. Account access, the model's actual
context/output limits and a successful final workflow still need verification.

## Coverage and compaction / 覆盖与压缩

- The plan records relative file paths, decoded-source hashes, character offsets,
  line ranges and complete serialized request sizes. Long files and even a single
  overlong line are split without discarding their tail.
- `report.json` distinguishes planned, completed, failed and unattempted chunks.
  `COMPLETE` applies only when every scanned fragment received a complete, valid
  model response. It does not certify that every bug was found.
- `compact-context.json` merges exact duplicate structured suggestions and keeps
  their evidence references. Original chunk input, raw response and analysis
  files remain available. Compaction costs no additional model call. Use
  `--no-compact` to retain duplicate suggestions in the combined result.
- `Review.md` provides the readable report. Suggestions must refer to a supplied
  file and line range. They remain model suggestions, requiring verification.

这里的压缩是在读完分块后，整理结构化建议和证据索引；不会先把未读源码
摘要掉，也不删除原始记录。分块之间的关联理解有限，不能声称一个模型在
同一时刻看到了整个项目。

## What the 100,000 budget means / 10万预算怎么计算

The planner conservatively counts UTF-8 bytes of the complete serialized request,
reserves the requested output plus a 2,048-unit protocol margin, and also obeys
the transport's request-size limit. This byte bound is a planning method, not
the selected model's exact tokenizer or a measurement of actual token usage.
Provider-reported usage stays separate. Raising this setting cannot enlarge a
model's own context window.

因此“10万”是可配置窗口预算，不是已证明每个模型都能接收10万真实输入token。
源码超出单次预算就继续分块；完整发送范围可以查证，模型是否正确理解每一行
不能靠覆盖百分比证明。

Supported extensions: Python, JavaScript, TypeScript, Java, C, C++, C/C++ headers,
Go, HTML, CSS, JSX, TSX and Rust. Other files and ignored dependency/build/output
directories are outside this scan. Links, binary/unreadable/oversized files are
excluded; warnings disclose relevant exclusions. The default per-file limit is
8 MB and can be explicitly changed with `--max-file-bytes`.

Known configured credentials are redacted before transport. Coverage refers to
the scanned decoded source; any redaction or UTF-8 replacement is disclosed.
The older `acv review` and `acv agent` retain their existing bounded behavior;
use this command when complete scanned-source coverage is required.

Current model documentation: [DeepSeek model limits](https://api-docs.deepseek.com/quick_start/pricing/),
[Nebius model metadata](https://docs.tokenfactory.nebius.com/api-reference/models/get-a-custom-model-by-short-name).
These describe provider capabilities, not a completed Nebius test of this build.
