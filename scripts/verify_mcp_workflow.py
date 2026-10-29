"""Execute a real official-SDK stdio client and challenge the exported CI gate.

No model/API call. The refund scenario is a controlled application adapter;
separate recorded evidence covers actual installed NVIDIA SDK versions.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def verify(output):
    from mcp import Client, StdioServerParameters

    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("refund_example", ROOT / "examples/refund-agent/capture.py")
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    example.capture(output / "captures")
    params = StdioServerParameters(command=sys.executable, args=["-m", "reviknot", "mcp", "--workspace", str(output)], cwd=str(ROOT))
    history = []
    async with Client(params) as client:
        listed = await client.list_tools()
        names = sorted(t.name for t in listed.tools)
        assert names == ["check_recording", "compare_recordings", "export_regression_gate", "inspect_boundary"]
        async def call(name, arguments):
            result = await client.call_tool(name, arguments)
            assert not result.is_error, (name, result.content)
            value = result.structured_content
            assert isinstance(value, dict)
            history.append({"tool": name, "arguments": arguments, "result": value})
            return value
        broken = await call("check_recording", {"recording_path": "captures/broken.recording.json"})
        fixed = await call("check_recording", {"recording_path": "captures/fixed.recording.json"})
        corrupt = await call("inspect_boundary", {"input_path": "captures/input.json", "output_path": "captures/corrupt.messages.json"})
        equal_broken = await call("compare_recordings", {"baseline_path": "captures/broken.recording.json", "candidate_path": "captures/broken.recording.json"})
        restored = await call("compare_recordings", {"baseline_path": "captures/broken.recording.json", "candidate_path": "captures/fixed.recording.json"})
        gate = await call("export_regression_gate", {"recording_path": "captures/broken.recording.json", "output_dir": "regression-gate"})
        denied = await client.call_tool("check_recording", {"recording_path": "../outside.json"})
        assert denied.is_error
    assert broken["status"] == "FAIL" and fixed["status"] == "PASS" and corrupt["status"] == "FAIL"
    assert equal_broken["status"] == "NEEDS_REVIEW"
    assert restored["status"] == "NEEDS_REVIEW" and restored["direction"] == "candidate_restores_contract"
    assert restored["contracts"]["candidate"]["status"] == "PASS"
    assert gate["status"] == "EXPORTED" and gate["observed_status"] == "FAIL"
    command = [sys.executable, "-I", "-S", "-m", "unittest", "discover", "-s", str(output/"regression-gate"), "-p", "test_boundary_contract.py"]
    tests = []
    for name, candidate, expected in (("broken", None, 1), ("fixed", "fixed", 0), ("corrupt", "corrupt", 1)):
        env = {k: v for k, v in os.environ.items() if k not in {"PATCHCOURT_CANDIDATE_TRACE", "PATCHCOURT_CANDIDATE_RECORDING", "PATCHCOURT_REQUEST_ID"}}
        if candidate:
            env["PATCHCOURT_CANDIDATE_RECORDING"] = str(output / "captures" / (candidate+".recording.json"))
        result = subprocess.run(command, cwd=output, env=env, capture_output=True, text=True, timeout=30)
        (output/("gate-"+name+".log")).write_text(result.stdout+result.stderr, encoding="utf-8")
        assert result.returncode == expected
        if expected:
            assert "Captured contract is not preserved" in result.stderr and "SEMANTIC_CHANGE" in result.stderr
        else:
            assert "Ran 1 test" in result.stderr and "\nOK" in result.stderr
        tests.append({"candidate":name, "expected_exit_code":expected, "actual_exit_code":result.returncode, "passed":True})
    from patchcourt import __version__
    evidence = {"status":"PASS", "kind":"Official MCP SDK client over actual stdio subprocess", "created_at":datetime.now(timezone.utc).isoformat(), "python":sys.version.split()[0], "transport":"stdio", "tools":names, "workflow":history, "gate_tests":tests, "path_escape_rejected":True, "provider_requests":0, "scope":"Controlled refund-agent application adapter; local data, no payment, model or arbitrary application execution. MCP host initiates tools; no background polling or autonomous editor trigger is claimed."}
    evidence['execution']={'reviknot_version':__version__, 'mcp_sdk_version':importlib.metadata.version('mcp'),
        'mcp_server_source_sha256':hashlib.sha256((ROOT/'patchcourt/mcp_server.py').read_bytes()).hexdigest(),
        'workflow_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'refund_example_source_sha256':hashlib.sha256((ROOT/'examples/refund-agent/capture.py').read_bytes()).hexdigest()}
    evidence['excluded_files']='Derived __pycache__/*.pyc runtime caches are not evidence inputs.'
    evidence["files"] = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*") if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    (output/"mcp-workflow.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"PASS", "transport":"stdio", "tools":len(names), "tool_calls":len(history), "gate_results":[x["actual_exit_code"] for x in tests], "provider_requests":0, "output":str(output)}))
    return evidence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    asyncio.run(verify(parser.parse_args().output))


if __name__ == "__main__":
    main()
