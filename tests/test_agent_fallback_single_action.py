import pytest

from acv.review_agent import AgentError, parse_agent_action, parse_agent_review


@pytest.mark.parametrize("raw", [
    '{"action":"read_file","arguments":{"path":"a.py"}} {"action":"read_file","arguments":{"path":"b.py"}}',
    '```json\n{"action":"read_file","arguments":{"path":"a.py"}}\n```\n```json\n{"action":"finish","reason":"done"}\n```',
    '{"action":"read_file","action":"finish","reason":"done"}',
    '{"action":"read_file","arguments":{"path":"a.py","start_line":NaN}}',
    '{"bad":{"action":"finish","reason":"inner"},"bad":2}',
])
def test_ambiguous_fallback_does_not_silently_execute_one_action(raw):
    with pytest.raises(AgentError):
        parse_agent_action(raw)


def test_one_wrapped_action_remains_usable():
    action = parse_agent_action('Here is the action:\n```json\n{"action":"read_file","arguments":{"path":"a.py"}}\n```')
    assert action.name == "read_file"
    assert action.arguments == {"path": "a.py"}


def test_final_review_does_not_silently_drop_second_report():
    with pytest.raises(AgentError):
        parse_agent_review('{"issues":[]} {"issues":[]}')
