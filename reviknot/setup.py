"""Unified installation checks, reproducible quickstart and MCP configuration."""
from __future__ import annotations

import asyncio
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

TOOLS = {'inspect_boundary', 'check_recording', 'compare_recordings', 'export_regression_gate'}


def _write(path, text):
    """Replace only our generated file; preserve a changed previous version."""
    if path.is_symlink() or not path.resolve().is_relative_to(path.parent.resolve()):
        raise ValueError('Configuration file cannot be a link: ' + str(path))
    data = text.encode('utf-8')
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + '.reviknot-backup-' + uuid4().hex[:8]))
    handle, name = tempfile.mkstemp(prefix='.reviknot-', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _json(path, value):
    _write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def _merge_client(root, target, entry):
    # Refuse linked configuration directories before making any changes.
    if not target.resolve().is_relative_to(root) or target.parent.is_symlink():
        raise ValueError('Client configuration must remain inside the selected workspace')
    document = json.loads(target.read_text(encoding='utf-8-sig')) if target.exists() else {}
    if not isinstance(document, dict) or not isinstance(document.get('mcpServers', {}), dict):
        raise ValueError('Existing client configuration is not an MCP server object')
    document.setdefault('mcpServers', {})['reviknot'] = entry
    _json(target, document)


async def _probe(workspace):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    parameters = StdioServerParameters(command=sys.executable, args=[
        '-m', 'reviknot', 'mcp', '--workspace', str(workspace)])
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            if names != TOOLS:
                raise ValueError('MCP discovery did not return all four ReviKnot tools')
            return sorted(names)


def doctor(workspace, *, probe=True):
    root = Path(workspace).resolve()
    if not root.is_dir():
        raise ValueError('Workspace must be an existing project directory')
    result = {'python': sys.version.split()[0], 'python_executable': sys.executable,
              'workspace': str(root), 'provider_requests': 0, 'dependencies': {}}
    for package in ('reviknot', 'openai', 'mcp'):
        try:
            result['dependencies'][package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            raise ValueError('Missing ' + package + '; install the complete application: python -m pip install -e .') from None
    if probe:
        try:
            result['mcp_tools'] = asyncio.run(asyncio.wait_for(_probe(root), timeout=30))
        except Exception as exc:
            raise ValueError('MCP connection check failed (' + type(exc).__name__
                             + '). Rerun python setup_reviknot.py and inspect the server diagnostic above.') from None
    result['status'] = 'PASS'
    return result


def setup_workspace(workspace, *, client='none', open_demo=False):
    if client not in {'none', 'codex', 'cursor', 'claude-code'}:
        raise ValueError('Unsupported MCP client')
    root = Path(workspace).resolve()
    if not root.is_dir():
        raise ValueError('Workspace must be an existing project directory')
    folder = root / '.reviknot'
    if folder.is_symlink():
        raise ValueError('The .reviknot configuration directory cannot be a link')
    checked = doctor(root)
    entry = {'command': sys.executable,
             'args': ['-m', 'reviknot', 'mcp', '--workspace', str(root)]}
    _json(folder / 'mcp.json', {'mcpServers': {'reviknot': entry}})
    _write(folder / 'codex.toml', '[mcp_servers.reviknot]\ncommand = ' + json.dumps(sys.executable)
           + '\nargs = ' + json.dumps(entry['args'], ensure_ascii=False) + '\n')
    selected_config = None
    if client == 'codex':
        executable = shutil.which('codex')
        if executable is None:
            raise ValueError('Codex CLI was not found. Generated configuration is ready in '
                             + str(folder) + '; add it through your client or rerun with --client codex after installing its CLI.')
        # User explicitly selected this client. The official CLI owns merging its configuration.
        try:
            subprocess.run([executable, 'mcp', 'add', 'reviknot', '--', entry['command'],
                            *entry['args']], check=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            raise ValueError('Codex registration did not complete. Generated MCP configuration is available in '
                             + str(folder) + '; check the client diagnostic above and rerun setup.') from None
        selected_config = 'Registered with the installed Codex CLI'
    elif client in {'cursor', 'claude-code'}:
        target = root / ('.cursor/mcp.json' if client == 'cursor' else '.mcp.json')
        _merge_client(root, target, entry)
        selected_config = str(target)
    from patchcourt.cli import main
    demo = folder / 'demo'
    if demo.exists():
        demo = folder / ('demo-' + uuid4().hex[:8])
    if main(['demo', '--output', str(demo)]) != 0:
        raise ValueError('The offline quickstart did not complete')
    result = {**checked, 'client': client, 'client_configuration': selected_config,
              'generated_configuration': str(folder), 'demo_directory': str(demo),
              'server_command': entry,
              'next': 'Restart your coding client and ask it to use the four ReviKnot tools.'
                      if client != 'none' else 'Choose --client codex, cursor or claude-code to connect your coding client.'}
    _json(folder / 'setup-result.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if open_demo:
        from patchcourt.cli import serve_static
        print('Opening the local demo at http://127.0.0.1:8765/ (Ctrl+C to stop).', flush=True)
        serve_static(demo, 8765, open_browser=True)
    return result
