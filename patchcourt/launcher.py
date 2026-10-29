"""Open a fresh, local, credential-free demonstration for desktop users."""
from pathlib import Path
import uuid

from .cli import serve_static
from .runner import demo


def main():
    output = Path("outputs") / ("desktop-" + uuid.uuid4().hex[:12])
    demo(output)
    print("ReviKnot offline demo — no API key required.", flush=True)
    print("Evidence: " + str(output.resolve()), flush=True)
    print("A free local port is selected automatically. Press Ctrl+C to stop.", flush=True)
    return serve_static(output, 0, open_browser=True)


if __name__ == "__main__":
    raise SystemExit(main())
