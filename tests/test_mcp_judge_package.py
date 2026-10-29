"""Synthetic receipt fixtures challenge the read-only MCP proof exporter.

These unit fixtures do not establish an actual official-client stdio session;
the separate real SDK integration and recorded release workflow do that.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

from patchcourt import __version__
from patchcourt.mcp_server import Workspace
from scripts import package_judge_demo as packager
from scripts.mcp_evidence import EXPECTED_FLOW, ROOT, verify_mcp_evidence
from tests.test_judge_package import sdk_fixture
from tests.test_patchcourt_recording_gate import run_gate
from tests.test_submission_check import workflow


def write(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def update_file_hashes(folder, report):
    report["files"] = {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in folder.rglob("*") if path.is_file() and path.name != "mcp-workflow.json"
                       and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    write(folder / "mcp-workflow.json", report)


@pytest.fixture
def mcp_fixture(tmp_path):
    folder = tmp_path / "proof";folder.mkdir()
    spec = importlib.util.spec_from_file_location("trusted_refund_fixture", ROOT / "examples/refund-agent/capture.py")
    example = importlib.util.module_from_spec(spec);spec.loader.exec_module(example)
    example.capture(folder / "captures")
    policy = Workspace(folder)
    history = [{"tool":name,"arguments":deepcopy(arguments),"result":getattr(policy,name)(**arguments)} for name,arguments in EXPECTED_FLOW]
    tests = []
    for scenario, code in (("broken",1),("fixed",0),("corrupt",1)):
        result = run_gate(folder / "regression-gate", recording=folder / f"captures/{scenario}.recording.json" if scenario != "broken" else None)
        assert result.returncode == code
        (folder / ("gate-"+scenario+".log")).write_text(result.stdout+result.stderr,encoding="utf-8")
        tests.append({"candidate":scenario,"expected_exit_code":code,"actual_exit_code":code,"passed":True})
    report = {"status":"PASS","kind":"Official MCP SDK client over actual stdio subprocess", "created_at":"2026-10-28T04:00:00+00:00",
              "python":"3.12.13","transport":"stdio","tools":sorted({name for name,_ in EXPECTED_FLOW}),"workflow":history,
              "gate_tests":tests,"path_escape_rejected":True,"provider_requests":0,
              "execution":{"reviknot_version":__version__,"mcp_sdk_version":"2.3.0",
                           "mcp_server_source_sha256":hashlib.sha256((ROOT/"patchcourt/mcp_server.py").read_bytes()).hexdigest(),
                           "workflow_script_sha256":hashlib.sha256((ROOT/"scripts/verify_mcp_workflow.py").read_bytes()).hexdigest(),
                           "refund_example_source_sha256":hashlib.sha256((ROOT/"examples/refund-agent/capture.py").read_bytes()).hexdigest()}}
    update_file_hashes(folder,report)
    return folder,report


def test_valid_mcp_proof_adds_a_distinct_card_and_complete_downloads(tmp_path,mcp_fixture):
    folder, report = mcp_fixture
    verified = verify_mcp_evidence(folder)
    assert verified["summary"]["gate_exits"] == [1,0,1]
    live,_ = workflow(tmp_path)
    sdk = sdk_fixture(tmp_path)
    output = tmp_path/"judge-mcp"
    result = packager.package(live,sdk,output,mcp_evidence=folder)
    page = (output/"index.html").read_text(encoding="utf-8")
    assert 'id="mcp-workflow"' in page and "recorded official SDK client" in page
    assert (output/"mcp-workflow.html").is_file() and (output/"MCP.md").is_file()
    if (ROOT/"MCP.zh-CN.md").is_file():
        assert (output/"MCP.zh-CN.md").read_bytes() == (ROOT/"MCP.zh-CN.md").read_bytes()
        assert 'href="MCP.zh-CN.md"' in page
    assert (output/"evidence/mcp/mcp-workflow.json").read_bytes() == (folder/"mcp-workflow.json").read_bytes()
    with zipfile.ZipFile(output/"refund-example.zip") as archive:
        assert archive.read("examples/refund-agent/capture.py") == (ROOT/"examples/refund-agent/capture.py").read_bytes()
    with zipfile.ZipFile(output/"mcp-proof.zip") as archive:
        assert archive.read("mcp-workflow.json") == (folder/"mcp-workflow.json").read_bytes()
        assert not any("__pycache__" in name for name in archive.namelist())
    with zipfile.ZipFile(result["archive"]) as archive:
        assert "mcp-workflow.html" in archive.namelist() and "refund-example.zip" in archive.namelist()


@pytest.mark.parametrize("mutation",["hash","version","source","script","example","request_count","call_order","arguments","result","exit","log","metadata","python","summary-type","gate-type","instructions","zip"])
def test_mcp_proof_mutations_are_rejected_before_output_creation(tmp_path,mcp_fixture,mutation):
    folder,report=mcp_fixture
    if mutation == "hash":report["files"]["captures/input.json"]="0"*64
    elif mutation == "version":report["execution"]["reviknot_version"]="0.0.0"
    elif mutation == "source":report["execution"]["mcp_server_source_sha256"]="0"*64
    elif mutation == "script":report["execution"]["workflow_script_sha256"]="0"*64
    elif mutation == "example":report["execution"]["refund_example_source_sha256"]="0"*64
    elif mutation == "request_count":report["provider_requests"]=False
    elif mutation == "call_order":report["workflow"][0],report["workflow"][1]=report["workflow"][1],report["workflow"][0]
    elif mutation == "arguments":report["workflow"][0]["arguments"]["recording_path"]="../outside.json"
    elif mutation == "result":report["workflow"][0]["result"]["status"]="PASS"
    elif mutation == "exit":report["gate_tests"][1]["actual_exit_code"]=False
    elif mutation == "log":
        (folder/"gate-fixed.log").write_text("FAILED\n",encoding="utf-8");update_file_hashes(folder,report)
    elif mutation == "metadata":report["execution"]="not an object"
    elif mutation == "python":report["python"]="2.7.18"
    elif mutation == "summary-type":
        summary_path=folder/"captures/capture-summary.json"
        summary=json.loads(summary_path.read_text(encoding="utf-8"))
        summary["verdicts"]["corrupt"]["findings"][0]["expected"]=0
        write(summary_path,summary);update_file_hashes(folder,report)
    elif mutation == "gate-type":report["workflow"][-1]["result"]["regression_gate"]["standalone_standard_library"]=1
    elif mutation == "instructions":report["workflow"][-1]["result"]["run_argv"]=["arbitrary-executable"]
    elif mutation == "zip":
        (folder/"regression-gate/regression-gate.zip").write_bytes(b"malformed archive")
        report["workflow"][-1]["result"]["regression_gate"]["archive_sha256"]=hashlib.sha256(b"malformed archive").hexdigest()
        update_file_hashes(folder,report)
    write(folder/"mcp-workflow.json",report)
    live,_=workflow(tmp_path)
    sdk=sdk_fixture(tmp_path)
    output=tmp_path/"rejected-export"
    with pytest.raises(ValueError):packager.package(live,sdk,output,mcp_evidence=folder)
    assert not output.exists()


def test_rehashed_malicious_gate_python_is_compared_as_bytes_and_never_run(tmp_path,mcp_fixture):
    folder,report=mcp_fixture
    marker=tmp_path/"executed.txt"
    malicious='from pathlib import Path\nPath('+repr(str(marker))+').write_text("executed")\n'
    (folder/"regression-gate/test_boundary_contract.py").write_text(malicious,encoding="utf-8")
    update_file_hashes(folder,report)
    with pytest.raises(ValueError,match="gate test"):
        verify_mcp_evidence(folder)
    assert not marker.exists()


@pytest.mark.parametrize("extra",["unexpected.txt","captures/.env.json"])
def test_unlisted_evidence_members_are_not_published(mcp_fixture,extra):
    folder,report=mcp_fixture
    (folder/extra).write_text("unexpected",encoding="utf-8")
    update_file_hashes(folder,report)
    with pytest.raises(ValueError,match="unexpected"):
        verify_mcp_evidence(folder)
