"""Mock-only regressions for complete replies and faithful source evidence."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acv.agent_tools import ProjectTools, ToolError
from acv.llm_client import LLMClient, LLMConfig, LLMError, LLMResponseError
from acv.review_agent import AgentError, run_reviewer_agent
from tests.fake_provider import FakeLLMProvider


def _reply(content=None, *, calls=None, finish="stop"):
    message = SimpleNamespace(content=content, tool_calls=calls)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish)]
    )


def _tool(name, **arguments):
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments))
    )


def _client(responses):
    captured = []
    pending = iter(responses)

    class Completions:
        def create(self, **kwargs):
            captured.append(kwargs)
            response = next(pending)
            if isinstance(response, Exception):
                raise response
            return response

    client = object.__new__(LLMClient)
    client.config = LLMConfig(api_key="unused-local-test", model="mock-model")
    client._native_tools_supported = None
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    return client, captured


def _read_reply():
    return _reply(calls=[_tool("read_file", path="app.py")], finish="tool_calls")


def _finish_reply():
    return _reply(calls=[_tool("finish", reason="Source inspected")], finish="tool_calls")


def _multiple_reply():
    return _reply(
        calls=[_tool("search_code", query="BUG"), _tool("read_file", path="app.py")],
        finish="tool_calls",
    )


def _issue(file, confidence="confirmed"):
    return json.dumps(
        {"issues": [{
            "severity": "high", "category": "bug", "file": file,
            "location": "line 1", "problem": "Unsafe operation",
            "evidence": "BUG marker", "why_it_matters": "Runtime failure",
            "suggested_improvement": "Validate the input", "confidence": confidence,
        }]}
    )


@pytest.mark.parametrize("method", ["complete", "complete_agent_action"])
@pytest.mark.parametrize("finish", ["length", "content_filter", "max_tokens"])
def test_incomplete_closed_json_is_rejected(method, finish):
    client, calls = _client([_reply('{"issues":[]}', finish=finish)])
    arguments = ("system", "source")
    if method == "complete_agent_action":
        arguments += ([],)
    with pytest.raises(LLMResponseError, match="incomplete output was rejected"):
        getattr(client, method)(*arguments)
    assert len(calls) == 1


def test_truncated_native_tool_call_is_not_accepted():
    client, calls = _client([
        _reply(calls=[_tool("read_file", path="app.py")], finish="length")
    ])
    with pytest.raises(LLMResponseError, match="truncated"):
        client.complete_agent_action("system", "source", [])
    assert len(calls) == 1


def test_multiple_native_calls_are_rejected_without_selecting_the_first():
    client, calls = _client([_multiple_reply()])
    with pytest.raises(LLMResponseError, match="None was executed"):
        client.complete_agent_action("system", "source", [])
    assert len(calls) == 1


def test_multiple_calls_recover_with_one_action_in_existing_retry_budget(tmp_path: Path):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    client, calls = _client([
        _multiple_reply(), _read_reply(), _finish_reply(), _reply('{"issues":[]}')
    ])
    tools = ProjectTools(tmp_path)
    result = run_reviewer_agent(client, tmp_path, max_steps=2, tools=tools)
    assert result.files_inspected == ["app.py"]
    assert result.steps_used == 2 and not result.stopped_by_limit
    assert [call[0] for call in tools.tool_calls] == ["list_files", "read_file"]
    assert len(calls) == 4
    assert "Return exactly one tool call" in calls[1]["messages"][1]["content"]


def test_repeated_multiple_calls_exhaust_three_attempts_without_tool_execution(tmp_path: Path):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    client, calls = _client([_multiple_reply() for _ in range(3)])
    tools = ProjectTools(tmp_path)
    with pytest.raises(AgentError, match="after 3 attempts"):
        run_reviewer_agent(client, tmp_path, max_steps=1, tools=tools)
    assert len(calls) == 3
    assert [call[0] for call in tools.tool_calls] == ["list_files"]
    assert tools.files_inspected == set()


def test_truncated_action_retries_without_executing_partial_action(tmp_path: Path):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    client, calls = _client([
        _reply('{"action":"finish","reason":"partial"}', finish="length"),
        _read_reply(), _finish_reply(), _reply('{"issues":[]}'),
    ])
    result = run_reviewer_agent(client, tmp_path, max_steps=2)
    assert result.files_inspected == ["app.py"]
    assert result.steps_used == 2
    assert len(calls) == 4
    assert "truncated" in calls[1]["messages"][1]["content"]


def test_truncated_final_review_retries_even_if_its_json_is_closed(tmp_path: Path):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    client, calls = _client([
        _read_reply(), _finish_reply(),
        _reply(_issue("app.py"), finish="length"), _reply('{"issues":[]}'),
    ])
    result = run_reviewer_agent(client, tmp_path)
    assert result.issues == []
    assert len(calls) == 4
    assert "truncated" in calls[-1]["messages"][1]["content"]


def test_final_truncation_exhausts_existing_three_attempts(tmp_path: Path):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    client, calls = _client([
        _read_reply(), _finish_reply(),
        *[_reply('{"issues":[]}', finish="length") for _ in range(3)],
    ])
    with pytest.raises(AgentError, match="after 3 attempts"):
        run_reviewer_agent(client, tmp_path)
    assert len(calls) == 5


def test_authentication_error_does_not_consume_format_retries(tmp_path: Path):
    class AuthenticationError(Exception):
        status_code = 401

    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    client, calls = _client([AuthenticationError("mock authentication failed")])
    with pytest.raises(LLMError, match="authentication failed"):
        run_reviewer_agent(client, tmp_path)
    assert len(calls) == 1


@pytest.mark.parametrize("confidence", ["confirmed", "possible"])
def test_search_only_file_is_not_eligible_for_final_findings(tmp_path: Path, confidence):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "unread.py").write_text("BUG = True\n", encoding="utf-8")
    provider = FakeLLMProvider([
        '{"action":"read_file","arguments":{"path":"app.py"}}',
        '{"action":"search_code","arguments":{"query":"BUG"}}',
        '{"action":"finish","reason":"Enough evidence"}',
        _issue("unread.py", confidence), '{"issues":[]}',
    ])
    tools = ProjectTools(tmp_path)
    result = run_reviewer_agent(provider, tmp_path, tools=tools)
    assert "unread.py" in tools.files_observed
    assert result.files_inspected == ["app.py"]
    assert result.issues == []
    assert "files not read with read_file: unread.py" in provider.calls[-1][1]


def test_search_followed_by_actual_read_allows_a_finding(tmp_path: Path):
    (tmp_path / "app.py").write_text("BUG = True\n", encoding="utf-8")
    provider = FakeLLMProvider([
        '{"action":"search_code","arguments":{"query":"BUG"}}',
        '{"action":"read_file","arguments":{"path":"app.py"}}',
        '{"action":"finish","reason":"Source inspected"}', _issue("app.py"),
    ])
    result = run_reviewer_agent(provider, tmp_path)
    assert result.files_inspected == ["app.py"]
    assert result.issues[0].file == "app.py"


def test_invalid_utf8_read_is_rejected_without_replacement_or_inspection(tmp_path: Path):
    source = tmp_path / "broken.py"
    original = b"value = 1\n# invalid byte: \xff\n"
    source.write_bytes(original)
    tools = ProjectTools(tmp_path)
    offset = original.index(b"\xff")
    with pytest.raises(ToolError, match=f"invalid UTF-8 at byte {offset}"):
        tools.execute("read_file", {"path": "broken.py"})
    assert source.read_bytes() == original
    assert tools.files_inspected == tools.files_observed == set()
    assert len(tools.warnings) == 1 and "broken.py" in tools.warnings[0]


def test_invalid_utf8_search_is_explicit_and_does_not_observe_corrupted_source(tmp_path: Path):
    (tmp_path / "broken.py").write_bytes(b"target = 1\n# \xff\n")
    (tmp_path / "valid.py").write_text("target = 2\n", encoding="utf-8")
    tools = ProjectTools(tmp_path)
    for query in ["target", "absent"]:
        result = tools.search_code(query)
        assert "Warning: skipped 1 file(s) with invalid UTF-8" in result
        assert "broken.py:1" not in result and "\ufffd" not in result
    assert tools.files_observed == {"valid.py"}
    assert tools.files_inspected == set()
    assert len(tools.warnings) == 1


def test_search_encoding_warning_output_stays_bounded(tmp_path: Path):
    for index in range(12):
        (tmp_path / f"broken{index:02}.py").write_bytes(b"target = '\xff'\n")
    tools = ProjectTools(tmp_path)
    result = tools.search_code("target")
    assert "skipped 12 file(s)" in result
    assert result.count("invalid UTF-8 at byte") == 10
    assert "additional encoding warnings omitted" in result
    assert len(tools.warnings) == 12


def test_agent_report_preserves_encoding_warning_and_valid_evidence(tmp_path: Path):
    (tmp_path / "broken.py").write_bytes(b"value = '\xff'\n")
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    provider = FakeLLMProvider([
        '{"action":"read_file","arguments":{"path":"broken.py"}}',
        '{"action":"read_file","arguments":{"path":"app.py"}}',
        '{"action":"finish","reason":"Valid source inspected"}', '{"issues":[]}',
    ])
    result = run_reviewer_agent(provider, tmp_path)
    assert result.files_inspected == ["app.py"]
    assert "invalid UTF-8" in result.observations[1].result
    assert any("broken.py" in warning and "invalid UTF-8" in warning for warning in result.warnings)


def test_read_past_eof_does_not_qualify_file_as_inspected(tmp_path: Path):
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    tools = ProjectTools(tmp_path)
    with pytest.raises(ToolError, match="no source lines were inspected"):
        tools.read_file("app.py", start_line=500)
    assert tools.files_inspected == tools.files_observed == set()


def test_empty_utf8_file_can_be_faithfully_inspected(tmp_path: Path):
    (tmp_path / "empty.py").write_bytes(b"")
    tools = ProjectTools(tmp_path)
    assert "File: empty.py" in tools.read_file("empty.py")
    assert tools.files_inspected == {"empty.py"}
