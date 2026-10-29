"""Install ReviKnot, all runtime tools and local MCP configuration in one step."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import venv


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='.', help='Your project directory')
    parser.add_argument('--client', choices=['none', 'codex', 'cursor', 'claude-code'], default='none')
    parser.add_argument('--open', action='store_true', help='Open the working local demo after setup')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error('Use Python 3.11 or newer to install the complete MCP-enabled application.')
    source = Path(__file__).resolve().parent
    environment = source / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    try:
        if not python.exists():
            print('Creating the local Python environment...', flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        print('Installing the complete application, including MCP and all four tools...', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-e', str(source)], check=True)
        command = [str(python), '-m', 'reviknot', 'setup', '--workspace',
                   str(Path(args.workspace).resolve()), '--client', args.client]
        if args.open:
            command.append('--open')
        return subprocess.run(command, cwd=source).returncode
    except (OSError, subprocess.CalledProcessError) as exc:
        print('Setup did not complete: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
