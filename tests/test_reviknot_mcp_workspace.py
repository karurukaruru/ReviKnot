"""MCP file and export policies are testable without the optional SDK."""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchcourt.cli import main
from patchcourt.mcp_server import Workspace, WorkspaceError, _public_payload, create_server
from tests.test_patchcourt_recording_gate import capture, run_gate, user_trace


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_message_verdict_preserves_exact_finding_paths_and_bounded_counts(tmp_path):
    original = user_trace()
    broken = deepcopy(original); broken[1].pop("tool_calls")
    write(tmp_path / "input.json", original); write(tmp_path / "output.json", broken)
    result = Workspace(tmp_path, max_findings=1).inspect_boundary("input.json", "output.json")
    assert result["status"] == "FAIL"
    assert result["finding_count"] > 1 and result["findings_truncated"] is True
    assert len(result["findings"]) == 1 and result["findings"][0]["path"].startswith("/")
    assert result["input_contract"]["status"] == "PASS"
    assert result["provider_requests"] == 0


@pytest.mark.parametrize("source", ["role", "field"])
def test_large_user_derived_diagnostics_have_bounded_strings_and_exact_metadata(tmp_path, source):
    original = user_trace()
    candidate = deepcopy(original)
    long = "X" * 100_000
    if source == "role":
        original[0]["role"] = long
    else:
        candidate[0][long] = "unsupported"
    write(tmp_path / "input.json", original)
    write(tmp_path / "output.json", candidate)
    result = Workspace(tmp_path, max_findings=1, max_finding_chars=128).inspect_boundary("input.json", "output.json")
    assert result["status"] == "INCONCLUSIVE" and result["finding_count"] == 1
    assert result["finding_fields_truncated"] is True
    finding = result["findings"][0]
    assert len(finding["message"]) == 128 and finding["message"].endswith("…")
    expected = ("Unsupported role: " if source == "role" else "Unsupported message fields: ") + long
    details = finding["field_truncation"]["message"]
    assert details == {"truncated": True, "characters": len(expected),
                       "sha256": hashlib.sha256(expected.encode()).hexdigest()}
    assert len(json.dumps(result)) < 4000


def test_large_finding_path_and_code_stay_strings_with_explicit_truncation(tmp_path):
    full_path = "/arguments/" + "key" * 1000
    full_code = "CODE" * 1000
    result = Workspace(tmp_path, max_finding_chars=64).verdict({"status":"FAIL", "findings":[
        {"code":full_code, "path":full_path, "message":"Ordinary diagnostic", "expected":1, "actual":2}]})
    finding = result["findings"][0]
    for key, full in (("path", full_path), ("code", full_code)):
        assert isinstance(finding[key], str) and len(finding[key]) == 64
        assert finding["field_truncation"][key] == {"truncated":True, "characters":len(full),
            "sha256":hashlib.sha256(full.encode()).hexdigest()}
    assert finding["message"] == "Ordinary diagnostic"


def test_diagnostic_size_limit_is_configurable_and_validated(tmp_path):
    value = {"status":"FAIL", "findings":[{"code":"LONG", "path":"/0", "message":"x"*3000}]}
    assert len(Workspace(tmp_path).verdict(value)["findings"][0]["message"]) == 2048
    expanded = Workspace(tmp_path, max_finding_chars=4096).verdict(value)
    assert expanded["finding_fields_truncated"] is False
    assert expanded["findings"][0]["message"] == "x"*3000
    for limit in (True, 0, 63, 65537):
        with pytest.raises(WorkspaceError, match="max_finding_chars"):
            Workspace(tmp_path, max_finding_chars=limit)


def test_source_checkout_install_guidance_works_without_published_project(tmp_path, monkeypatch):
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "mcp.server":
            raise ImportError("optional SDK missing")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(WorkspaceError) as caught:
        create_server(tmp_path)
    assert 'pip install -e ".[mcp]"' in str(caught.value)
    assert 'pip install "mcp>=2,<3"' in str(caught.value)


def test_mcp_cli_bounds_tool_failure_diagnostics_and_keeps_stdout_clean(tmp_path, monkeypatch, capsys):
    import patchcourt.mcp_server
    message = "Invalid or ambiguous recording: " + "X"*100_000
    def fail(*args, **kwargs):
        raise WorkspaceError(message)
    monkeypatch.setattr(patchcourt.mcp_server, "serve", fail)
    assert main(["mcp", "--workspace", str(tmp_path), "--max-finding-chars", "128"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and len(captured.err) < 300
    assert "truncated; original_characters=" + str(len(message)) in captured.err
    assert hashlib.sha256(message.encode()).hexdigest() in captured.err


def test_captured_comparison_checks_original_input_and_unhealthy_baseline(tmp_path):
    old, _ = capture(tmp_path)
    future, _ = capture(tmp_path, broken=False, name="future.json", version="2", request="other")
    policy = Workspace(tmp_path)
    assert policy.check_recording(old.name)["status"] == "FAIL"
    result = policy.compare_recordings(old.name, future.name)
    assert result["status"] == "NEEDS_REVIEW"
    assert result["direction"] == "candidate_restores_contract"
    assert result["contracts"]["candidate"]["status"] == "PASS"
    equal_broken = policy.compare_recordings(old.name, old.name)
    assert equal_broken["status"] == "NEEDS_REVIEW"
    changed = json.loads(future.read_text());changed["events"][0]["payload"][0]["content"] = "Different contract"
    write(future, changed)
    with pytest.raises(WorkspaceError, match="same valid original input"):
        policy.compare_recordings(old.name, future.name)


@pytest.mark.parametrize("value", ["../outside.json", "/outside.json", "C:\\secrets.json", "\\\\host\\share\\file.json",
                                    ".env", ".env.local", "sub/.env.json", "credentials.json", ".ssh/key.json",
                                    "local-secrets.json", "api-keys.json", "client.credentials.json",
                                    ".git/config.json", "file.json:secret", "space. /file.json", "./file.json", "a//file.json",
                                    "a\x00.json", "", "file.pem"])
def test_private_escape_and_ambiguous_paths_are_rejected_before_reads(tmp_path, value):
    with pytest.raises(WorkspaceError):
        Workspace(tmp_path).read(value)


@pytest.mark.parametrize("encoded", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":', b'\xff'])
def test_strict_file_parsing_rejects_ambiguous_json_and_invalid_utf8(tmp_path, encoded):
    (tmp_path / "bad.json").write_bytes(encoded)
    with pytest.raises(WorkspaceError, match="UTF-8 JSON"):
        Workspace(tmp_path).read("bad.json")


@pytest.mark.parametrize("value", [{"api_key": "do-not-leak-this-value"}, {"authorization":"Bearer do-not-leak"},
                                    {"text":"tvly-" + "this-is-a-synthetic-secret"}, {"nested":[{"cookie":"session=private"}]},
                                    {"content":'{"client_secret":"do-not-leak-this-value"}'},
                                    {"content":'{"nested":"{\\"token\\":\\"do-not-leak-this-value\\"}"}'}])
def test_sensitive_payloads_are_rejected_without_echoing_contents(tmp_path, value):
    write(tmp_path / "payload.json", value)
    with pytest.raises(WorkspaceError) as caught:
        Workspace(tmp_path).read("payload.json")
    assert "do-not-leak" not in str(caught.value) and "session=private" not in str(caught.value)


def test_size_bounds_are_explicit_and_configurable(tmp_path):
    (tmp_path / "data.json").write_text('["long payload"]', encoding="utf-8")
    with pytest.raises(WorkspaceError, match="max_file_bytes"):
        Workspace(tmp_path, max_file_bytes=4).read("data.json")
    assert Workspace(tmp_path, max_file_bytes=64).read("data.json")[0] == ["long payload"]
    for options in ({"max_file_bytes":True},{"max_file_bytes":0},{"max_findings":0},{"max_findings":10001}):
        with pytest.raises(WorkspaceError):Workspace(tmp_path, **options)


def test_redacted_capture_is_inconclusive_and_cannot_export_a_gate(tmp_path):
    path, _ = capture(tmp_path)
    value = json.loads(path.read_text());value["events"][0]["payload_redacted"] = True
    write(path, value)
    policy = Workspace(tmp_path)
    assert policy.check_recording(path.name)["status"] == "INCONCLUSIVE"
    assert policy.compare_recordings(path.name, path.name)["status"] == "INCONCLUSIVE"
    with pytest.raises(WorkspaceError, match="unredacted"):
        policy.export_regression_gate(path.name, "new-gate")
    assert not (tmp_path / "new-gate").exists()


def test_export_reuses_standard_library_gate_and_never_reads_env_or_overwrites(tmp_path, monkeypatch):
    path, _ = capture(tmp_path)
    # Existing evidence.sanitize consults environment; the MCP writer must not.
    import patchcourt.evidence
    monkeypatch.setattr(patchcourt.evidence, "sanitize", lambda _value: (_ for _ in ()).throw(AssertionError("environment sanitizer used")))
    result = Workspace(tmp_path).export_regression_gate(path.name, "nested/gate with spaces")
    gate = tmp_path / "nested/gate with spaces"
    assert result["status"] == "EXPORTED" and result["regression_gate"]["default_test_expected"] == "FAIL"
    assert "run_command" not in result and result["run_argv"][5] == "nested/gate with spaces"
    assert run_gate(gate).returncode == 1
    fixed = tmp_path / "fixed.json";write(fixed,user_trace())
    assert run_gate(gate, trace=fixed).returncode == 0
    contract = gate / "contract.json";original = contract.read_bytes()
    with pytest.raises(WorkspaceError, match="new directory"):
        Workspace(tmp_path).export_regression_gate(path.name, "nested/gate with spaces")
    assert contract.read_bytes() == original


def test_symlink_and_hardlink_inputs_are_not_read(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside.json");write(outside, user_trace())
    link = tmp_path / "link.json"
    try:link.symlink_to(outside)
    except OSError:pass  # Windows standard users may lack symlink privileges.
    else:
        with pytest.raises(WorkspaceError, match="Symlinks"):
            Workspace(tmp_path).read(link.name)
    hard = tmp_path / "hard.json"
    try:os.link(outside, hard)
    except OSError:pytest.skip("Filesystem does not support hard links")
    with pytest.raises(WorkspaceError, match="Hard-linked"):
        Workspace(tmp_path).read(hard.name)


def test_reparse_attribute_is_rejected_even_without_symlink_type(tmp_path, monkeypatch):
    write(tmp_path / "data.json", [])
    original = Path.lstat
    def metadata(path):
        result = original(path)
        return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400) if path.name == "data.json" else result
    monkeypatch.setattr(Path, "lstat", metadata)
    with pytest.raises(WorkspaceError, match="reparse"):
        Workspace(tmp_path).read("data.json")


def test_mcp_cli_does_not_load_env_file_or_pollute_stdout(tmp_path, monkeypatch, capsys):
    import patchcourt.credentials
    monkeypatch.setattr(patchcourt.credentials, "load_local_credentials", lambda path: (_ for _ in ()).throw(AssertionError("credential loader called")))
    assert main(["--env-file", "private.env", "mcp", "--workspace", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "does not load credential files" in captured.err
