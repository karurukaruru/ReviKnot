"""CLI contract and streaming ID regressions; all provider work is mocked."""
import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest

from patchcourt.cli import main
from patchcourt.counterexamples import tool_conversation
from patchcourt import providers
from patchcourt.semantic import compare_messages, reconstruct_stream


@pytest.mark.parametrize("status,expected", [
    ("PASS", 0), ("FAIL", 1), ("BLOCKED", 2), ("INCONCLUSIVE", 2),
    ("NEEDS_REVIEW", 2), ("UNKNOWN", 2),
])
def test_live_exit_code_distinguishes_regression_from_uncertainty(tmp_path, status, expected):
    report = {"status": status, "total_reported_tokens": 0}
    with patch("patchcourt.live_workflow.run_live_workflow", return_value=report) as run, redirect_stdout(io.StringIO()) as output:
        assert main(["live", "--provider", "nebius", "--model", "nvidia/test-Nemotron",
                     "--output", str(tmp_path / "live")]) == expected
    assert json.loads(output.getvalue())["status"] == status
    assert run.call_args.kwargs["provider"] == "nebius"
    assert not (tmp_path / "live").exists()


def test_live_missing_key_through_real_workflow_returns_uncertainty(tmp_path):
    target = tmp_path / "missing-key"
    with patch.dict("os.environ", {}, clear=True), patch.object(providers, "_transport") as transport, redirect_stdout(io.StringIO()) as output:
        assert main(["live", "--provider", "deepseek", "--output", str(target)]) == 2
    transport.assert_not_called()
    assert json.loads(output.getvalue())["status"] == "BLOCKED"
    report = json.loads((target / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "BLOCKED"
    assert len(report["requests"]) == 1
    assert report["requests"][0]["http_attempted"] is False
    assert "task" not in report


@pytest.mark.parametrize("http_status", [401, 429, 503])
def test_live_http_failure_through_mock_transport_is_not_a_regression(tmp_path, http_status):
    target = tmp_path / "unavailable"
    response = (http_status, {}, '{"error":{"message":"Synthetic HTTP failure"}}')
    with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "synthetic-cli-test-key"}, clear=True), patch.object(
            providers, "_transport", return_value=response) as transport, redirect_stdout(io.StringIO()) as output:
        assert main(["live", "--provider", "deepseek", "--output", str(target)]) == 2
    transport.assert_called_once()
    assert json.loads(output.getvalue())["status"] == "INCONCLUSIVE"
    report = json.loads((target / "report.json").read_text(encoding="utf-8"))
    assert report["requests"][0]["http_status"] == http_status
    assert "task" not in report


def test_live_rejected_mapping_through_mock_transport_remains_a_regression(tmp_path):
    target = tmp_path / "bad-mapping"
    bad_plan = {"source": "tool_calls", "id_field": "name", "name_field": "name", "arguments_field": "args",
                "arguments_encoding": "json", "preserve_legacy": True, "empty_content": "null"}
    body = {"model": "deepseek-flash", "choices": [{"finish_reason": "stop", "message": {
        "role": "assistant", "content": json.dumps(bad_plan)}}], "usage": {"total_tokens": 10}}
    with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "synthetic-cli-test-key"}, clear=True), patch.object(
            providers, "_transport", return_value=(200, {}, json.dumps(body))) as transport, redirect_stdout(io.StringIO()) as output:
        assert main(["live", "--provider", "deepseek", "--output", str(target)]) == 1
    assert transport.call_count == 3
    assert json.loads(output.getvalue())["status"] == "FAIL"
    report = json.loads((target / "report.json").read_text(encoding="utf-8"))
    assert report["verification"]["status"] == "REJECTED"
    assert len(report["repair_attempts"]) == 3
    assert "task" not in report


def _executed(messages):
    return {"status": "EXECUTED", "input_conversion": {"status": "PASS"}, "output": messages}


def test_boundary_default_shows_repaired_candidate_without_certifying_bad_baseline(tmp_path):
    original = tool_conversation()
    broken = [dict(message) for message in original]
    broken[0].pop("tool_calls")
    runs = {"upstream": _executed(broken), "reviewed-patch": _executed(original)}
    # Keep actual input-contract comparison and report export; isolate the worker
    # execution so this regression needs neither an SDK nor network access.
    with patch("patchcourt.boundary_run._run_side", side_effect=lambda messages, variant, sdk: runs[variant]) as run, redirect_stdout(io.StringIO()) as output:
        assert main(["boundary-run", "--output", str(tmp_path / "repair")]) == 2
    summary = json.loads(output.getvalue())
    assert summary == {
        "status": "NEEDS_REVIEW", "output": str((tmp_path / "repair").resolve()),
        "provider_requests": 0, "baseline_variant": "upstream", "candidate_variant": "reviewed-patch",
        "baseline_contract": "FAIL", "candidate_contract": "PASS", "difference_status": "NEEDS_REVIEW",
        "direction": "candidate_restores_contract",
    }
    assert [call.args[1] for call in run.call_args_list] == ["upstream", "reviewed-patch"]
    report = json.loads((tmp_path / "repair" / "report.json").read_text(encoding="utf-8"))
    assert report["cases"][0]["task_replay"]["after"]["inventory_value"] == 21


def test_boundary_explicit_reverse_remains_a_failing_regression_control(tmp_path):
    original = tool_conversation()
    broken = [dict(message) for message in original]
    broken[0].pop("tool_calls")
    runs = {"upstream": _executed(broken), "reviewed-patch": _executed(original)}
    with patch("patchcourt.boundary_run._run_side", side_effect=lambda messages, variant, sdk: runs[variant]), redirect_stdout(io.StringIO()) as output:
        assert main(["boundary-run", "--baseline", "reviewed-patch", "--candidate", "upstream",
                     "--output", str(tmp_path / "regression")]) == 1
    summary = json.loads(output.getvalue())
    assert summary["status"] == "FAIL"
    assert summary["baseline_contract"] == "PASS"
    assert summary["candidate_contract"] == "FAIL"
    assert summary["direction"] == "regression"
    assert compare_messages(original, broken)["status"] == "FAIL"


def _stream_with_ids(identifiers):
    events = []
    for position, ident in enumerate(identifiers):
        call = {"index": 0}
        if ident is not None:
            call["id"] = ident
        if position == 0:
            call["function"] = {"name": "quote", "arguments": "{}"}
        events.append({"choices": [{"index": 0, "delta": {"tool_calls": [call]},
                                    "finish_reason": "tool_calls" if position == len(identifiers) - 1 else None}]})
    return events


@pytest.mark.parametrize("ident", ["call_quote", "opaque-id", "42"])
def test_stream_repeated_complete_id_is_not_duplicated(ident):
    result = reconstruct_stream(_stream_with_ids([ident, "", None, ident, ident]))
    assert result["tool_calls"][0]["id"] == ident
    conversation = [result, {"role": "tool", "tool_call_id": ident, "content": "ready"}]
    assert compare_messages(conversation, conversation)["status"] == "PASS"


@pytest.mark.parametrize("first,second", [
    ("call_quote", "call_cost"), ("alpha", "beta"),
    ("call_quote", "call_quote_extra"), ("call_quote", "quote"),
])
def test_stream_conflicting_complete_ids_are_never_guessed_or_merged(first, second):
    with pytest.raises(ValueError, match="Conflicting streaming tool call IDs at index 0"):
        reconstruct_stream(_stream_with_ids([first, second]))


def test_stream_real_id_fragments_require_explicit_protocol_selection():
    events = _stream_with_ids(["call_", "quote"])
    with pytest.raises(ValueError, match="documented ID-delta protocol"):
        reconstruct_stream(events)
    assert reconstruct_stream(events, tool_call_id_mode="fragment")["tool_calls"][0]["id"] == "call_quote"


def test_stream_fragment_mode_preserves_repeated_and_overlapping_fragments():
    events = _stream_with_ids(["call_", "ab", "ab", "bc"])
    assert reconstruct_stream(events, tool_call_id_mode="fragment")["tool_calls"][0]["id"] == "call_ababbc"


def test_stream_repeated_ids_are_scoped_per_interleaved_call_index():
    events = [{"choices": [{"delta": {"tool_calls": [
        {"index": 1, "id": "call_b", "function": {"name": "second", "arguments": '{"city":"'}},
        {"index": 0, "id": "call_a", "function": {"name": "first", "arguments": "{"}},
    ]}}]}, {"choices": [{"delta": {"tool_calls": [
        {"index": 0, "id": "call_a", "function": {"arguments": "}"}},
        {"index": 1, "id": "call_b", "function": {"arguments": '東京"}'}},
    ]}, "finish_reason": "tool_calls"}]}]
    calls = reconstruct_stream(events)["tool_calls"]
    assert [call["id"] for call in calls] == ["call_a", "call_b"]
    assert [json.loads(call["function"]["arguments"]) for call in calls] == [{}, {"city": "東京"}]


@pytest.mark.parametrize("mode", [None, "auto", "unknown", 0, []])
def test_stream_unknown_id_modes_are_rejected(mode):
    with pytest.raises(ValueError, match="tool_call_id_mode must be"):
        reconstruct_stream(_stream_with_ids(["call_quote"]), tool_call_id_mode=mode)
