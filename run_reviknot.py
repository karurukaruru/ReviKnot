"""Run the local installation without activating its environment."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parent
python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if not python.exists():
    print('Run python setup_reviknot.py first, or use the installed reviknot command.', file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(subprocess.run([str(python), '-m', 'reviknot', *sys.argv[1:]]).returncode)
