"""Installation paths must work with spaces and preserve other MCP servers."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from reviknot import setup


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / 'My project 中文'
    root.mkdir()
    monkeypatch.setattr(setup, 'doctor', lambda root: {
        'status': 'PASS', 'provider_requests': 0, 'mcp_tools': sorted(setup.TOOLS)})
    return root


def test_setup_installs_all_tool_configuration_and_runs_a_real_offline_example(workspace, monkeypatch):
    from patchcourt import providers
    request = Mock(side_effect=AssertionError('Offline setup must not call a provider'))
    monkeypatch.setattr(providers, 'request', request)
    result = setup.setup_workspace(workspace)
    document = json.loads((workspace / '.reviknot/mcp.json').read_text(encoding='utf-8'))
    entry = document['mcpServers']['reviknot']
    assert Path(entry['command']).is_absolute()
    assert entry['args'] == ['-m', 'reviknot', 'mcp', '--workspace', str(workspace)]
    assert Path(result['demo_directory'], 'index.html').is_file()
    assert result['mcp_tools'] == sorted(setup.TOOLS)
    assert result['provider_requests'] == 0
    assert not (workspace / '.cursor').exists()
    assert not (workspace / '.mcp.json').exists()
    request.assert_not_called()


@pytest.mark.parametrize('client,relative', [('cursor', '.cursor/mcp.json'), ('claude-code', '.mcp.json')])
def test_client_setup_merges_preserves_and_is_idempotent(workspace, client, relative):
    target = workspace / relative
    target.parent.mkdir(exist_ok=True)
    original = {'theme': 'existing', 'mcpServers': {'other': {'command': 'keep-me'}}}
    target.write_text(json.dumps(original), encoding='utf-8')
    setup.setup_workspace(workspace, client=client)
    first = target.read_bytes()
    saved = json.loads(first)
    assert saved['theme'] == 'existing'
    assert saved['mcpServers']['other'] == original['mcpServers']['other']
    assert saved['mcpServers']['reviknot']['args'][-1] == str(workspace)
    assert len(list(target.parent.glob(target.name + '.reviknot-backup-*'))) == 1
    setup.setup_workspace(workspace, client=client)
    assert target.read_bytes() == first
    assert len(list(target.parent.glob(target.name + '.reviknot-backup-*'))) == 1


def test_invalid_existing_client_json_is_preserved(workspace):
    target = workspace / '.mcp.json'
    target.write_text('{do not overwrite broken config', encoding='utf-8')
    original = target.read_bytes()
    with pytest.raises(ValueError):
        setup.setup_workspace(workspace, client='claude-code')
    assert target.read_bytes() == original


def test_codex_registration_uses_argument_array_and_verified_interpreter(workspace, monkeypatch):
    monkeypatch.setattr(setup.shutil, 'which', lambda name: '/client path/codex')
    run = Mock()
    monkeypatch.setattr(setup.subprocess, 'run', run)
    result = setup.setup_workspace(workspace, client='codex')
    assert run.call_args.args[0] == ['/client path/codex', 'mcp', 'add', 'reviknot', '--',
        setup.sys.executable, '-m', 'reviknot', 'mcp', '--workspace', str(workspace)]
    assert run.call_args.kwargs == {'check': True, 'timeout': 30}
    assert result['client_configuration'].startswith('Registered')


def test_missing_codex_reports_an_actionable_error_with_generated_config(workspace, monkeypatch):
    monkeypatch.setattr(setup.shutil, 'which', lambda name: None)
    with pytest.raises(ValueError, match='Codex CLI was not found'):
        setup.setup_workspace(workspace, client='codex')
    assert (workspace / '.reviknot/codex.toml').is_file()


def test_linked_client_configuration_never_writes_outside_workspace(workspace, tmp_path):
    outside = tmp_path / 'outside.json'
    outside.write_text('{}', encoding='utf-8')
    try:
        (workspace / '.mcp.json').symlink_to(outside)
    except OSError:
        pytest.skip('Creating links requires Windows developer mode or permission')
    with pytest.raises(ValueError):
        setup.setup_workspace(workspace, client='claude-code')
    assert outside.read_text(encoding='utf-8') == '{}'
