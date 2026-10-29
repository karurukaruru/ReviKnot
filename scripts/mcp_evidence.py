"""Read-only verification of a saved official-client MCP workflow receipt.

Only current trusted project comparators run. Supplied Python, tests, examples
and logs are inspected as bytes and never imported or executed.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import zipfile

from patchcourt import __version__
from patchcourt.evidence import digest, strict_json
from patchcourt.mcp_server import Workspace
from patchcourt.recording_export import GATE_TEST, PORTABLE_GATE_FILES
from patchcourt.semantic import compare_messages
from scripts.submission_check import public_evidence, timestamp


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = {"captures/input.json", "captures/capture-summary.json"} | {
    f"captures/{name}.{kind}.json" for name in ("broken", "fixed", "corrupt") for kind in ("messages", "recording")}
GATE_FILES = {"regression-gate/" + name for name in PORTABLE_GATE_FILES} | {"regression-gate/regression-gate.zip"}
LOGS = {"gate-" + name + ".log" for name in ("broken", "fixed", "corrupt")}
PROOF_FILES = CAPTURES | GATE_FILES | LOGS
EXPECTED_FLOW = [
    ("check_recording", {"recording_path": "captures/broken.recording.json"}),
    ("check_recording", {"recording_path": "captures/fixed.recording.json"}),
    ("inspect_boundary", {"input_path": "captures/input.json", "output_path": "captures/corrupt.messages.json"}),
    ("compare_recordings", {"baseline_path": "captures/broken.recording.json", "candidate_path": "captures/broken.recording.json"}),
    ("compare_recordings", {"baseline_path": "captures/broken.recording.json", "candidate_path": "captures/fixed.recording.json"}),
    ("export_regression_gate", {"recording_path": "captures/broken.recording.json", "output_dir": "regression-gate"}),
]


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _link(path):
    metadata = path.lstat()
    return stat.S_ISLNK(metadata.st_mode) or bool(getattr(metadata, "st_file_attributes", 0) & 0x400)


def verify_mcp_evidence(folder):
    folder = Path(folder)
    if not folder.is_dir() or _link(folder):
        raise ValueError("MCP proof must be a regular directory")
    folder = folder.resolve()
    found = set()
    for base, directories, names in os.walk(folder, followlinks=False):
        kept = []
        for name in directories:
            path = Path(base) / name
            relative = path.relative_to(folder).as_posix()
            if _link(path):
                raise ValueError("MCP proof contains a directory link or reparse point")
            if relative in {"regression-gate/__pycache__", "regression-gate/_patchcourt_contract/__pycache__"}:
                continue
            if relative not in {"captures", "regression-gate", "regression-gate/_patchcourt_contract"}:
                raise ValueError("MCP proof contains an unexpected directory")
            kept.append(name)
        directories[:] = kept
        for name in names:
            path = Path(base) / name
            relative = path.relative_to(folder).as_posix()
            if _link(path) or relative not in PROOF_FILES | {"mcp-workflow.json"}:
                raise ValueError("MCP proof contains an unexpected file or link")
            found.add(relative)
    if found != PROOF_FILES | {"mcp-workflow.json"}:
        raise ValueError("MCP proof file set is incomplete")
    files = {}
    for name in sorted(found):
        path = folder / name
        if not path.is_file() or path.stat().st_size > 8_000_000:
            raise ValueError("MCP proof file is not regular or exceeds 8 MB")
        with path.open("rb") as stream:
            data = stream.read(8_000_001)
        if len(data) > 8_000_000:
            raise ValueError("MCP proof file exceeds 8 MB")
        files[name] = data
        if not name.endswith(".zip"):
            public_evidence(data.decode("utf-8-sig"))
    if sum(map(len, files.values())) > 32_000_000:
        raise ValueError("MCP proof exceeds its aggregate size limit")
    report = strict_json(files["mcp-workflow.json"].decode("utf-8-sig"))
    public_evidence(report)
    if (not isinstance(report, dict) or report.get("status") != "PASS"
            or report.get("kind") != "Official MCP SDK client over actual stdio subprocess"
            or report.get("transport") != "stdio" or not timestamp(report.get("created_at"))
            or type(report.get("provider_requests")) is not int or report["provider_requests"] != 0
            or report.get("path_escape_rejected") is not True
            or report.get("tools") != sorted({name for name, _ in EXPECTED_FLOW})
            or report.get("files") != {name: _sha(data) for name, data in files.items() if name != "mcp-workflow.json"}):
        raise ValueError("MCP receipt identity, file hashes or request scope differs")
    python_version = re.fullmatch(r"3\.([0-9]+)\.[0-9]+(?:[A-Za-z0-9.+-]*)?", str(report.get("python", "")))
    if python_version is None or int(python_version[1]) < 11:
        raise ValueError("MCP receipt requires a Python 3.11+ execution version")
    execution = report.get("execution", {})
    if not isinstance(execution, dict):
        raise ValueError("MCP execution metadata must be an object")
    expected_sources = {"mcp_server_source_sha256": ROOT / "patchcourt/mcp_server.py",
                        "workflow_script_sha256": ROOT / "scripts/verify_mcp_workflow.py"}
    if "refund_example_source_sha256" in execution:
        expected_sources["refund_example_source_sha256"] = ROOT / "examples/refund-agent/capture.py"
    if (execution.get("reviknot_version") != __version__
            or not re.fullmatch(r"2\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.+-]*)?", str(execution.get("mcp_sdk_version", "")))
            or any(execution.get(key) != _sha(path.read_bytes()) for key, path in expected_sources.items())):
        raise ValueError("MCP execution version or trusted source fingerprint differs")
    workflow = report.get("workflow")
    if not isinstance(workflow, list) or len(workflow) != len(EXPECTED_FLOW):
        raise ValueError("MCP receipt must contain the six expected tool calls")
    policy = Workspace(folder)
    for row, (name, arguments) in zip(workflow, EXPECTED_FLOW):
        if (not isinstance(row, dict) or set(row) != {"tool", "arguments", "result"}
                or row.get("tool") != name or row.get("arguments") != arguments
                or not isinstance(row.get("result"), dict)
                or type(row["result"].get("provider_requests")) is not int or row["result"]["provider_requests"] != 0):
            raise ValueError("MCP workflow tool order, arguments or request scope differs")
        if name != "export_regression_gate":
            fresh = getattr(policy, name)(**arguments)
            if digest(fresh) != digest(row["result"]):
                raise ValueError("MCP tool result differs from fresh local captured-data validation")
    for scenario, expected_status in (("broken", "FAIL"), ("fixed", "PASS"), ("corrupt", "FAIL")):
        selected, _ = policy.selected(f"captures/{scenario}.recording.json", None)
        messages = strict_json(files[f"captures/{scenario}.messages.json"].decode("utf-8-sig"))
        original = strict_json(files["captures/input.json"].decode("utf-8-sig"))
        if (digest(selected["candidate"]) != digest(messages) or digest(selected["original_input"]) != digest(original)
                or selected["adapter"] != "refund-application-adapter"
                or selected["payload_redacted"] or compare_messages(original, messages)["status"] != expected_status):
            raise ValueError("MCP capture sidecars do not establish the three controlled scenarios")
    _verify_refund_domain(original, workflow[2]["result"])
    summary = strict_json(files["captures/capture-summary.json"].decode("utf-8-sig"))
    if (not isinstance(summary, dict) or type(summary.get("provider_requests")) is not int or summary["provider_requests"] != 0
            or digest(summary.get("verdicts")) != digest({name: compare_messages(original, strict_json(files[f"captures/{name}.messages.json"].decode("utf-8-sig")))
                                                        for name in ("broken", "fixed", "corrupt")})):
        raise ValueError("MCP capture summary differs from independently checked scenarios")
    tests = report.get("gate_tests")
    expected_tests = [{"candidate": name, "expected_exit_code": code, "actual_exit_code": code, "passed": True}
                      for name, code in (("broken", 1), ("fixed", 0), ("corrupt", 1))]
    if tests != expected_tests or any(type(row["actual_exit_code"]) is not int or type(row["expected_exit_code"]) is not int or row["passed"] is not True for row in tests):
        raise ValueError("MCP gate controls must record broken/fixed/corrupt exits 1/0/1")
    for name in ("broken", "fixed", "corrupt"):
        log = files["gate-" + name + ".log"].decode("utf-8-sig")
        if ("Ran 1 test" not in log or (name == "fixed" and ("\nOK" not in log or "FAILED" in log))
                or (name != "fixed" and ("Captured contract is not preserved" not in log or "SEMANTIC_CHANGE" not in log))):
            raise ValueError("MCP gate log does not support the recorded control")
    _verify_gate(files, workflow[-1]["result"], policy)
    downloads = {"MCP.md": (ROOT / "MCP.md").read_bytes(),
                 "examples/refund-agent/capture.py": (ROOT / "examples/refund-agent/capture.py").read_bytes(),
                 "examples/refund-agent/README.md": (ROOT / "examples/refund-agent/README.md").read_bytes(),
                 "LICENSE": (ROOT / "LICENSE").read_bytes()}
    if (ROOT / "MCP.zh-CN.md").is_file():
        downloads["MCP.zh-CN.md"] = (ROOT / "MCP.zh-CN.md").read_bytes()
    for data in downloads.values():
        public_evidence(data.decode("utf-8-sig"))
    return {"report": report, "files": files, "downloads": downloads,
            "summary": {"tools": len(report["tools"]), "tool_calls": len(workflow), "gate_exits": [1, 0, 1],
                        "new_provider_requests": 0, "captured_official_client_stdio": True,
                        "mcp_server_source_sha256": execution["mcp_server_source_sha256"]}}


def _verify_gate(files, result, policy):
    """Compare the portable gate to current own-project source without running it."""
    gate_files = {name: files["regression-gate/" + name] for name in PORTABLE_GATE_FILES}
    selected, recording_sha = policy.selected("captures/broken.recording.json", None)
    contract = strict_json(gate_files["contract.json"].decode("utf-8-sig"))
    observed = strict_json(gate_files["observed-candidate.json"].decode("utf-8-sig"))
    version_source = gate_files["_patchcourt_contract/version_snapshot.py"]
    if version_source.decode("utf-8").replace("\r\n", "\n") != '__version__ = ' + repr(__version__) + '\n':
        raise ValueError("MCP gate version snapshot differs from current version")
    runtime = {"_patchcourt_contract/version_snapshot.py": version_source,
               "_patchcourt_contract/LICENSE": (ROOT / "patchcourt/fixtures/PATCHCOURT-LICENSE").read_bytes()}
    runtime.update({"_patchcourt_contract/" + name: (ROOT / "patchcourt" / name).read_bytes()
                    for name in ("evidence.py", "semantic.py", "recording.py")})
    if any(gate_files[name] != data for name, data in runtime.items()):
        raise ValueError("MCP gate runtime differs from current trusted source")
    expected_contract = {"schema_version": "1.0", "kind": "captured-boundary-regression-contract",
                         "adapter": selected["adapter"], "captured_version": selected["version"], "request_id": selected["request_id"],
                         "expected_input": selected["original_input"], "observed_status": "FAIL",
                         "runtime_files_sha256": {name: _sha(data) for name, data in runtime.items()},
                         "observed_candidate_file_sha256": _sha(gate_files["observed-candidate.json"]),
                         "scope": "Checks captured messages, not future SDK execution; the source recording is user-supplied and is not independently authenticated"}
    if digest(contract) != digest(expected_contract) or digest(observed) != digest(selected["candidate"]):
        raise ValueError("MCP frozen gate contract differs from captured messages")
    contract_sha = _sha(gate_files["contract.json"])
    if gate_files["test_boundary_contract.py"].decode("utf-8").replace("\r\n", "\n") != GATE_TEST.replace("CONTRACT_SHA256", contract_sha).replace("\r\n", "\n"):
        raise ValueError("MCP gate test differs from exact reviewed template")
    gate = result.get("regression_gate", {})
    expected_gate = {"status": "EXPORTED", "default_candidate_status": "FAIL", "default_test_expected": "FAIL",
                     "standalone_standard_library": True, "runtime_files_sha256": expected_contract["runtime_files_sha256"],
                     "contract_file_sha256": contract_sha, "test_file_sha256": _sha(gate_files["test_boundary_contract.py"]),
                     "download_file": "regression-gate.zip", "archive_sha256": _sha(files["regression-gate/regression-gate.zip"])}
    if (digest(gate) != digest(expected_gate) or result.get("status") != "EXPORTED" or result.get("observed_status") != "FAIL"
            or result.get("output_dir") != "regression-gate" or result.get("recording_file_sha256") != recording_sha):
        raise ValueError("MCP exported gate receipt differs from verified artifacts")
    if (result.get("run_argv") != ["python", "-m", "unittest", "discover", "-s", "regression-gate", "-p", "test_boundary_contract.py"]
            or result.get("run_from") != "configured workspace"):
        raise ValueError("MCP gate run instructions differ from the non-executing trusted tool")
    try:
        with zipfile.ZipFile(io.BytesIO(files["regression-gate/regression-gate.zip"])) as archive:
            members = archive.infolist()
            if (len(members) != len(gate_files) or {row.filename for row in members} != set(gate_files)
                    or sum(row.file_size for row in members) > 20_000_000):
                raise ValueError("MCP gate ZIP member allowlist differs")
            for row in members:
                if row.is_dir() or row.flag_bits & 1 or stat.S_ISLNK(row.external_attr >> 16) or archive.read(row) != gate_files[row.filename]:
                    raise ValueError("MCP gate ZIP member differs from reviewed artifact")
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError):
        raise ValueError("MCP gate ZIP is malformed or unreadable") from None


def _verify_refund_domain(original, corrupted):
    """The portal's concrete example claims must follow from the actual data."""
    try:
        calls = original[2]["tool_calls"]
        names = [row["function"]["name"] for row in calls]
        policy = strict_json(calls[1]["function"]["arguments"])
        order = strict_json(original[3]["content"])
        approval = strict_json(original[4]["content"])
        draft = strict_json(original[5]["content"])
        typed_corruption = any(row.get("code") == "SEMANTIC_CHANGE"
                               and row.get("path") == "/2/tool_calls/1/args/condition/opened"
                               and row.get("expected") is False and type(row.get("actual")) is int and row["actual"] == 0
                               for row in corrupted["findings"])
        valid = (len(original) == 6 and names == ["lookup_order", "check_return_policy"]
                 and policy["condition"]["opened"] is False and policy["reason"] == "商品未拆封"
                 and order["currency"] == draft["currency"] == "EUR" and draft["action"] == "refund_draft"
                 and type(draft["amount_cents"]) is int and draft["amount_cents"] == 7990
                 and approval["requires_human_approval"] is True and draft["requires_human_approval"] is True
                 and typed_corruption)
    except (IndexError, KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("MCP refund-domain claims are not supported by the captured data")
