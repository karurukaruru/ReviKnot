"""Verify the built wheel actually contains and executes its packaged resources."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from patchcourt import __version__

ROOT = Path(__file__).resolve().parents[1]
wheel = ROOT / "dist" / (sys.argv[1] if len(sys.argv)>1 else f"agent_code_validator-{__version__}-py3-none-any.whl")
(ROOT / ".local-tmp").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT / ".local-tmp") as tmp:
    target = Path(tmp)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("Unsafe wheel entry")
        archive.extractall(target / "installed")
    script = "import sys; sys.path.insert(0, sys.argv[1]); from patchcourt.cli import main; raise SystemExit(main(['demo','--output',sys.argv[2]]))"
    result = subprocess.run([sys.executable, "-I", "-c", script, str(target / "installed"), str(target / "report")], cwd=target, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr)
    report = json.loads((target / "report" / "report.json").read_text(encoding="utf-8"))
    assert report["summary"]["fail"] == 11 and report["summary"]["pass"] == 3
    assert (target / "report" / "index.html").is_file()
    assert (target / "installed" / "patchcourt" / "web" / "live.html").is_file()
    entrypoints = next(n for n in names if n.endswith("entry_points.txt"))
    assert "patchcourt = patchcourt.cli:main" in (target / "installed" / entrypoints).read_text()
    boundary_script = "import sys; sys.path.insert(0, sys.argv[1]); from patchcourt.cli import main; raise SystemExit(main(['boundary-run','--output',sys.argv[2]]))"
    boundary = subprocess.run([sys.executable, "-I", "-c", boundary_script, str(target / "installed"), str(target / "boundary")], cwd=target, capture_output=True, text=True, timeout=60)
    assert boundary.returncode == 1, boundary.stderr
    boundary_report = json.loads((target / "boundary" / "report.json").read_text(encoding="utf-8"))
    assert boundary_report["status"] == "FAIL"
    assert all(r["status"] == "EXECUTED" for r in boundary_report["executions"].values())
    assert boundary_report["cases"][0]["contracts"]["baseline"]["status"] == "PASS"
    assert (target / "installed" / "patchcourt" / "fixtures" / "nvidia-upgrade-constraints.txt").is_file()
    upgrade_script = "import sys; sys.path.insert(0,sys.argv[1]); from patchcourt.cli import main; raise SystemExit(main(['upgrade-run',sys.argv[2],'--from-version','1.4.3','--to-version','1.5.0','--environment-dir',sys.argv[3],'--output',sys.argv[4]]))"
    upgrade = subprocess.run([sys.executable, "-I", "-c", upgrade_script, str(target / "installed"), str(target), str(target / "missing-envs"), str(target / "upgrade")], cwd=target, capture_output=True, text=True, timeout=30)
    assert upgrade.returncode == 2, upgrade.stderr
    upgrade_report = json.loads((target / "upgrade" / "report.json").read_text(encoding="utf-8"))
    assert upgrade_report["status"] == "INCONCLUSIVE" and upgrade_report["provider_requests"] == 0
    capture_script = ("import sys;sys.path.insert(0,sys.argv[1]);from patchcourt.recorder import BoundaryRecorder;"
                      "r=BoundaryRecorder('wheel-adapter','1');"
                      "r.transform([{'role':'user','content':'preserve this'}],lambda messages:[{'role':'user','content':'changed'}]);"
                      "r.save(sys.argv[2])")
    subprocess.run([sys.executable, "-I", "-S", "-c", capture_script, str(target / "installed"), str(target / "capture.json")],
                   cwd=target, capture_output=True, text=True, check=True, timeout=20)
    gate_script = "import sys;sys.path.insert(0,sys.argv[1]);from patchcourt.cli import main;raise SystemExit(main(['check-recording',sys.argv[2],'--output',sys.argv[3]]))"
    captured = subprocess.run([sys.executable, "-I", "-S", "-c", gate_script, str(target / "installed"),
                               str(target / "capture.json"), str(target / "gate")], cwd=target,
                              capture_output=True, text=True, timeout=30)
    assert captured.returncode == 1, captured.stderr
    standalone = subprocess.run([sys.executable, "-I", "-S", "-m", "unittest", "discover", "-s", str(target / "gate"),
                                 "-p", "test_boundary_contract.py"], cwd=target,
                                capture_output=True, text=True, timeout=20)
    assert standalone.returncode == 1 and "Captured contract is not preserved" in standalone.stderr, standalone.stderr
    assert (target / "installed" / "patchcourt" / "fixtures" / "PATCHCOURT-LICENSE").is_file()
    local_source = target / "large_source.py"
    local_source.write_text("# source data only\n" + "entry = 1\n" * 7000 + "# TAIL_FROM_WHEEL\n", encoding="utf-8")
    source_script = "import sys;sys.path.insert(0,sys.argv[1]);from patchcourt.cli import main;raise SystemExit(main(['review-source',sys.argv[2],'--dry-run','--output',sys.argv[3]]))"
    planned = subprocess.run([sys.executable, "-I", "-S", "-c", source_script, str(target / "installed"),
                              str(local_source), str(target / "source-plan")], cwd=target,
                             capture_output=True, text=True, timeout=30)
    assert planned.returncode == 0, planned.stderr
    source_report = json.loads((target / "source-plan" / "report.json").read_text(encoding="utf-8"))
    assert source_report["status"] == "PLANNED" and source_report["provider_request_invocations"] == 0
    ranges = [fragment for chunk in source_report["chunks"] for fragment in chunk["fragments"]]
    assert ranges[0]["char_start"] == 0 and ranges[-1]["char_end"] == source_report["source_characters"]
    assert all(left["char_end"] == right["char_start"] for left, right in zip(ranges, ranges[1:]))
    print(json.dumps({"status":"PASS", "wheel":wheel.name, "isolated_mode":True, "summary":report["summary"], "entrypoint":"patchcourt", "fixtures_and_dashboard":True, "boundary_workers_executed_from_wheel":True, "upgrade_runner_and_constraints_packaged":True, "captured_boundary_exports_standalone_gate_without_site_packages":True, "full_source_planner_without_site_packages":True, "source_characters_planned":source_report["source_characters"], "source_planning_provider_calls":0}))
