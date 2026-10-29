"""Real official-SDK client→stdio process→tools, including standalone gates.

Run with the optional MCP environment. No model, HTTP or credential is used.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

mcp = pytest.importorskip("mcp", reason="Optional official MCP SDK is not installed")
if not hasattr(mcp, "Client"):
    pytest.skip("MCP integration requires official SDK v2", allow_module_level=True)
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from tests.test_patchcourt_recording_gate import capture, run_gate, user_trace


ROOT = Path(__file__).resolve().parents[1]


def params(root, *options):
    return StdioServerParameters(command=sys.executable, args=["-m", "reviknot", "mcp", "--workspace", str(root), *options], cwd=ROOT)


def data(result):
    assert result.is_error is False, result.content
    assert isinstance(result.structured_content, dict)
    return result.structured_content


def test_official_client_initializes_lists_calls_and_exports_real_stdio_tools(tmp_path):
    broken, _ = capture(tmp_path)
    fixed, _ = capture(tmp_path, broken=False, name="fixed-recording.json", version="2", request="next")
    original = tmp_path / "input.json";original.write_text(json.dumps(user_trace()), encoding="utf-8")
    bad = deepcopy(user_trace());bad[1].pop("tool_calls")
    (tmp_path / "output.json").write_text(json.dumps(bad), encoding="utf-8")
    async def exercise():
        async with Client(params(tmp_path), mode="legacy", read_timeout_seconds=15) as client:
            assert client.server_info.name == "ReviKnot"
            assert client.server_capabilities.tools is not None
            tools = {tool.name:tool for tool in (await client.list_tools()).tools}
            assert set(tools) == {"inspect_boundary", "check_recording", "compare_recordings", "export_regression_gate"}
            assert set(tools["inspect_boundary"].input_schema["required"]) == {"input_path", "output_path"}
            for name in ("inspect_boundary", "check_recording", "compare_recordings"):
                assert tools[name].annotations.read_only_hint is True
                assert tools[name].annotations.open_world_hint is False
            assert tools["export_regression_gate"].annotations.read_only_hint is False
            assert tools["export_regression_gate"].annotations.destructive_hint is False
            assert tools["export_regression_gate"].annotations.idempotent_hint is False
            boundary = data(await client.call_tool("inspect_boundary", {"input_path":"input.json", "output_path":"output.json"}))
            assert boundary["status"] == "FAIL" and any(finding["path"] for finding in boundary["findings"])
            observed = data(await client.call_tool("check_recording", {"recording_path":broken.name}))
            assert observed["status"] == "FAIL" and observed["provider_requests"] == 0
            compared = data(await client.call_tool("compare_recordings", {"baseline_path":broken.name,"candidate_path":fixed.name}))
            assert compared["status"] == "NEEDS_REVIEW" and compared["direction"] == "candidate_restores_contract"
            assert compared["contracts"]["candidate"]["status"] == "PASS"
            gate = data(await client.call_tool("export_regression_gate", {"recording_path":broken.name,"output_dir":"ci/gate"}))
            assert gate["status"] == "EXPORTED" and gate["regression_gate"]["default_test_expected"] == "FAIL"
            again = await client.call_tool("export_regression_gate", {"recording_path":broken.name,"output_dir":"ci/gate"})
            assert again.is_error is True
    asyncio.run(exercise())
    gate = tmp_path / "ci/gate"
    assert run_gate(gate).returncode == 1
    assert run_gate(gate, trace=original).returncode == 0
    # Corrupting a frozen artifact must fail; no dishonest all-green fixture.
    contract = gate / "contract.json"
    contract.write_text(contract.read_text() + " ", encoding="utf-8")
    corrupted = run_gate(gate, trace=original)
    assert corrupted.returncode == 1 and "Frozen contract changed" in corrupted.stderr


def test_real_stdio_errors_do_not_crash_the_server_or_leak_credentials(tmp_path):
    recording, _ = capture(tmp_path)
    (tmp_path / "malformed.json").write_text('{"x":1,"x":2}',encoding="utf-8")
    (tmp_path / "private.json").write_text('{"api_key":"do-not-echo-private-content"}',encoding="utf-8")
    (tmp_path / ".env.json").write_text('{}',encoding="utf-8")
    (tmp_path / "long-role.json").write_text(json.dumps([{"role":"X"*100_000,"content":""}]),encoding="utf-8")
    (tmp_path / "input.json").write_text(json.dumps(user_trace()),encoding="utf-8")
    async def exercise():
        async with Client(params(tmp_path, "--max-finding-chars", "128"), read_timeout_seconds=15) as client:
            assert client.protocol_version
            for arguments in ({"recording_path":"../outside.json"}, {"recording_path":"malformed.json"},
                              {"recording_path":"private.json"}, {"recording_path":".env.json"},
                              {"recording_path":42}, {}):
                result = await client.call_tool("check_recording", arguments)
                assert result.is_error is True
                assert "do-not-echo-private-content" not in str(result.content)
            long_result = data(await client.call_tool("inspect_boundary", {"input_path":"input.json", "output_path":"long-role.json"}))
            assert long_result["status"] == "INCONCLUSIVE" and long_result["finding_fields_truncated"] is True
            assert len(long_result["findings"][0]["message"]) == 128
            assert long_result["findings"][0]["field_truncation"]["message"]["characters"] > 100_000
            assert data(await client.call_tool("check_recording", {"recording_path":recording.name}))["status"] == "FAIL"
    asyncio.run(exercise())
