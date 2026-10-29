# PatchCourt — testing guide / 测试说明

This guide covers the current development build. It distinguishes a recorded model workflow from a fresh inference request. It is not evidence that pending Nebius/NVIDIA execution has occurred.

本说明适用于当前开发包，区分保存的模型运行记录与新推理请求；不证明尚未完成的Nebius/NVIDIA实测。

## English

### Requirements and the easiest start

Use Python **3.10 or newer**, Windows/Linux/macOS and a modern browser. Extract the judge-demo ZIP before opening files. On Windows, double-click `Start-Judge-Demo.cmd`. On any supported desktop platform, run from the extracted folder:

```bash
python launch_demo.py
```

The launcher selects a free localhost port and opens a browser. It installs nothing and the recorded demonstration sends no provider requests. Keep its terminal open; stop with Ctrl+C. If the browser does not open automatically, use the localhost URL printed by the launcher. If `python` is unavailable on Windows but the Python launcher is installed, use `py -3 launch_demo.py`.

### What to inspect

1. Select **Replay the verified repair**. This replays a saved actual development-provider workflow. Read the provider and provenance labels rather than interpreting playback as new inference.
2. Inspect the mapping checks, corrupted-repair rejection and inventory result **21** in the saved evidence. Editorial playback timing is not provider latency.
3. Select **Inspect a real SDK upgrade**. The separately executed unmodified SDK releases are checked against the original input. **NEEDS_REVIEW** is the expected result when both releases share the defect.
4. Download the complete CI gate. Extract it, open a terminal in its folder and run:

```bash
python -I -S -m unittest discover -s . -p test_boundary_contract.py
```

The bundled observed candidate is intentionally broken, so this test is expected to fail. That red test proves detection of the supplied defect; it is not a launcher failure. The complete gate includes the frozen input, observed candidate, checker source and license. Read `REGRESSION-GATE.md` in the gate for candidate inputs.

### Run your own small capture-to-CI example

Use the source archive, change into its root (the folder containing `pyproject.toml`) and run the following separately. No API or optional SDK package is required:

```bash
python examples/captured-boundary/capture.py --output outputs/courier-broken.json
python -m patchcourt check-recording outputs/courier-broken.json --output outputs/courier-gate
python -I -S -m unittest discover -s outputs/courier-gate -p test_boundary_contract.py
python examples/captured-boundary/capture.py --fixed --output outputs/courier-fixed.json
```

The check command returns **1**, and the first generated test is red. To test the corrected capture against the **same** gate, use PowerShell:

```powershell
$env:PATCHCOURT_CANDIDATE_RECORDING = (Resolve-Path outputs/courier-fixed.json).Path
python -I -S -m unittest discover -s outputs/courier-gate -p test_boundary_contract.py
Remove-Item Env:PATCHCOURT_CANDIDATE_RECORDING
```

Or bash:

```bash
PATCHCOURT_CANDIDATE_RECORDING="$PWD/outputs/courier-fixed.json" python -I -S -m unittest discover -s outputs/courier-gate -p test_boundary_contract.py
```

The corrected candidate should pass. This controlled courier adapter is a dependency-free example, separate from the real installed-SDK evidence. The gate checks supplied messages; it does not execute an arbitrary future SDK or run generated Python.

### Inspect the current development runs

The source archive retains `evidence/development-052/final-deepseek-live-01/report.json` and `final-deepseek-reuse-01/report.json`. Both are **PASS**. The initial run used three model requests (4,094 reported tokens); the reuse run had an exact knowledge hit, reran all eight checks and the corruption/task controls, and used two requests (655 tokens). The observed task result is 21 in each. These measurements describe these runs; no general savings or required-platform claim follows.

The separate `deepseek-evaluation-01/benchmark.json` is **PARTIAL**, with an incomplete second original-ACV baseline response. Both direct-model and Tavily-assisted arms matched 18/24 outcomes on two repetitions of the same 12 developer-authored cases. Failed/unexecuted cases remain in the report. This small experiment shows no retrieval improvement and is not a blind generalization benchmark.

### Offline source viewer and evidence

From the source root:

```bash
python -m patchcourt demo --output outputs/judge-demo
python -m patchcourt serve outputs/judge-demo --port 8765
```

Open `http://127.0.0.1:8765`. Choose another port if needed. The NVIDIA case displays the historical defect, reviewed repair and deterministic recovery. The CrewAI/Gemini case verifies image serialization; preserved bytes do not establish a completed live vision task. Saved request bodies, hashes, controls, failures and scope are available with the evidence.

Fresh inference requires separately configured legitimate provider access and can incur usage charges; this offline package does not request a judge's API key. The final submission must state how the intended judging workflow remains free and clearly identify the actual required-platform run. At this checkpoint that run is still pending.

For a setup problem, record OS, Python version, command and error text, excluding secrets. `README.md`, `TESTING.md` and `CAPTURED_BOUNDARIES.md` in the source root explain scope and troubleshooting. Do not interpret an unavailable optional dependency or missing credential as a passing test.

## 简体中文

### 环境与最快启动

需要Python **3.10或更新版本**、Windows/Linux/macOS和现代浏览器。先解压评委演示ZIP。在Windows双击 `Start-Judge-Demo.cmd`；也可以在解压目录运行：

```bash
python launch_demo.py
```

启动器自动选择可用的本地端口并打开浏览器，不安装软件，保存记录的演示不会发起模型请求。保留终端窗口，结束时按Ctrl+C。浏览器没打开时，复制启动器打印的本地网址。如果Windows只有Python启动器，可用 `py -3 launch_demo.py`。

### 看哪些内容

1. 选择 **Replay the verified repair**，查看实际开发供应商运行的已保存记录。页面上的供应商和来源标签说明它不是新推理。
2. 查看字段映射检查、故意破坏修复后的拒绝结果，以及库存结果 **21**。回放剪辑时间不是供应商延迟。
3. 选择 **Inspect a real SDK upgrade**。两个真实安装且未修改的SDK版本分别与原始输入比较；两个版本都含相同缺陷时，**NEEDS_REVIEW**是正确结果。
4. 下载完整CI门禁，解压后在其目录运行：

```bash
python -I -S -m unittest discover -s . -p test_boundary_contract.py
```

附带的候选记录故意保留坏结果，因此测试应该失败。这表示抓到了该缺陷，不是程序启动失败。完整包包含冻结输入、实际候选、检查器源码和许可证。如何提供新候选见门禁内的 `REGRESSION-GATE.md`。

### 自己走一遍“捕获→CI”

解压源码包，进入含 `pyproject.toml` 的根目录。按英文部分的四条命令**逐条**运行：捕获坏结果、导出门禁、运行门禁、捕获修复结果。无需API或可选SDK依赖。检查命令返回1，第一次门禁为红，都是预期行为。

然后按上面的PowerShell或bash命令，把 `outputs/courier-fixed.json` 作为新候选提供给**同一个**门禁。修复结果应通过。此处是一个受控应用适配器示例，独立于真实已安装SDK的执行证据；门禁不会替你执行未来SDK或模型代码。

### 检查本轮真实开发运行

源码 `evidence/development-052/final-deepseek-live-01/report.json` 和 `final-deepseek-reuse-01/report.json` 均为 **PASS**。首次3次模型请求、4094个报告token；复用命中相同身份的知识，仍重验全部8项检查及破坏控制和工具任务，2次请求、655个token。两次任务结果都是21。这只是对应运行的实际数据，不能外推普遍节省或指定平台资格。

单独的 `deepseek-evaluation-01/benchmark.json` 为 **PARTIAL**，第二轮原版ACV基线回复不完整。直接模型与Tavily辅助组在同样12个开发者编写样例的两次重复中，各匹配18/24个结果。失败或未执行项保留，没有观察到检索提升，也不能称为独立盲测。

### 离线查看器与证据

在源码根目录运行上面的 `demo`、`serve` 两条命令，打开 `http://127.0.0.1:8765`。若端口占用可换端口。NVIDIA案例展示历史缺陷、审查过的修复和确定性恢复；CrewAI/Gemini案例验证图片序列化，不能把字节保留说成已经完成真实视觉任务。

新推理需要另行配置合法供应商访问，可能产生用量费用；离线演示不会向评委索要API密钥。最终提交仍需说明完整评审流程如何免费使用，并指明真正的指定平台运行。当前这项仍未完成。

启动有问题时，保留系统、Python版本、命令和错误文字，移除所有密钥。源码根目录 `README.md`、`TESTING.md`、`CAPTURED_BOUNDARIES.md` 有说明。可选依赖或密钥缺失应如实标注，不能算测试通过。
