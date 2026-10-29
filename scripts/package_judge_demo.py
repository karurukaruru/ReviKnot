"""Build a free static judge demo from verified, recorded execution evidence.

The replay is explicitly labeled; the package has no credential or inference
endpoint. Its source report and every included request keep their integrity keys.
"""
import argparse
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import stat
import zipfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from patchcourt import __version__
from patchcourt.evidence import digest, strict_json
from scripts.submission_check import public_evidence, read_json, verify_workflow

LAUNCHER = '''"""Serve this exported judge demo locally. No installation or API access."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import unquote, urlsplit
import webbrowser

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    try:
        manifest_bytes = (directory / "package-manifest.json").read_bytes()
        if len(manifest_bytes) > 1_000_000:
            raise ValueError("Package manifest exceeds its size limit")
        files = json.loads(manifest_bytes)["files"]
        if not isinstance(files, dict) or not 1 <= len(files) <= 2000:
            raise ValueError("Invalid package file list")
        for name, checksum in files.items():
            if (not isinstance(name, str) or not name or name.startswith("/") or "\\\\" in name
                    or PurePosixPath(name).as_posix() != name or ".." in PurePosixPath(name).parts
                    or not isinstance(checksum, str) or not re.fullmatch("[0-9a-f]{64}", checksum)):
                raise ValueError("Invalid package file entry")
        files["package-manifest.json"] = hashlib.sha256(manifest_bytes).hexdigest()
    except (KeyError, OSError, ValueError, TypeError):
        parser.error("The judge package manifest is missing or invalid. Extract the complete demo ZIP into a new folder.")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_file(False)

        def do_HEAD(self):
            self.send_file(True)

        def send_file(self, head):
            if self.headers.get("Host", "").lower() not in {
                "127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port)
            }:
                self.send_error(403)
                return
            name = unquote(urlsplit(self.path).path).lstrip("/") or "index.html"
            if name not in files:
                self.send_error(404)
                return
            path = directory / name
            try:
                if not path.resolve().is_relative_to(directory):
                    raise ValueError("File leaves the exported package")
                for component in (path, *path.parents):
                    if component == directory:
                        break
                    metadata = component.lstat()
                    if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
                        raise ValueError("Package links are not served")
                if not path.is_file() or path.stat().st_size > 50_000_000:
                    raise ValueError("Invalid package file")
                with path.open("rb") as stream:
                    data = stream.read(50_000_001)
                if len(data) > 50_000_000 or hashlib.sha256(data).hexdigest() != files[name]:
                    raise ValueError("Package file changed after export")
            except (OSError, ValueError):
                self.send_error(404)
                return
            content_type = {".html": "text/html; charset=utf-8", ".json": "application/json",
                            ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
                            ".py": "text/plain; charset=utf-8", ".cmd": "text/plain; charset=utf-8",
                            ".zip": "application/zip", ".whl": "application/zip"}.get(path.suffix.lower(), "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            if not head:
                self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = "http://127.0.0.1:" + str(server.server_port) + "/"
    print(url, flush=True)
    print("Recorded evidence only. No API key required. Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
'''

WINDOWS_LAUNCHER = '''@echo off
setlocal
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0launch_demo.py"
    goto :finished
)
where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0launch_demo.py"
    goto :finished
)
echo Python 3 is required. Install Python, then double-click this file again.
:finished
if errorlevel 1 pause
endlocal
'''

def verified_report(folder):
    report, manifest = read_json(folder / "report.json"), read_json(folder / "manifest.json")
    if (not isinstance(report, dict) or not isinstance(manifest, dict)
            or not report.get("run_id") or report["run_id"] != manifest.get("run_id")
            or digest(report) != manifest.get("report_sha256")):
        raise ValueError("Source report integrity does not match its manifest")
    public_evidence(report)
    public_evidence(manifest)
    return report


def verify_sdk_report(report):
    """The portal's fixed narrative requires this exact recorded comparison."""
    from patchcourt.boundary_run import SDK_RELEASES
    from patchcourt.semantic import compare_messages
    if (report.get("mode") != "upgrade-run" or report.get("status") != "NEEDS_REVIEW"
            or not isinstance(report.get("cases"), list) or len(report["cases"]) != 1
            or report.get("provider_requests") != 0):
        raise ValueError("SDK inspector requires the recorded unhealthy-baseline installed-release comparison")
    case = report["cases"][0]
    provenance = case.get("provenance", {})
    if (case.get("execution") is not True or case.get("status") != "NEEDS_REVIEW"
            or provenance.get("dependency") != "langchain-nvidia-ai-endpoints"
            or provenance.get("baseline_version") != "1.4.3" or provenance.get("candidate_version") != "1.5.0"):
        raise ValueError("SDK narrative requires unmodified NVIDIA releases 1.4.3 and 1.5.0")
    executions, environments = report.get("executions", {}), report.get("environments", {})
    if set(executions) != {"baseline", "candidate"} or set(environments) != {"baseline", "candidate"}:
        raise ValueError("Both installed SDK executions and environments are required")
    for side, version in (("baseline", "1.4.3"), ("candidate", "1.5.0")):
        run, env = executions[side], environments[side]
        identity = run.get("provenance", {})
        if (run.get("status") != "EXECUTED" or run.get("input_conversion", {}).get("status") != "PASS"
                or run.get("output") != case.get(side) or run.get("provider_requests") != 0
                or identity.get("backend") != "installed-sdk" or identity.get("real_sdk_classes") is not True
                or identity.get("version") != version or identity.get("source_sha256") != SDK_RELEASES[version]
                or identity.get("executed_source_sha256") != SDK_RELEASES[version]
                or env.get("status") != "READY" or env.get("version") != version):
            raise ValueError("SDK report does not bind the claimed installed releases to their executed source and output")
    original, baseline, candidate = report.get("input"), case.get("baseline"), case.get("candidate")
    contracts = {"baseline": compare_messages(original, baseline), "candidate": compare_messages(original, candidate),
                 "difference": compare_messages(baseline, candidate)}
    if (contracts != case.get("contracts") or contracts["baseline"]["status"] != "FAIL"
            or contracts["candidate"]["status"] != "FAIL" or baseline != candidate
            or not any(row.get("code") == "UNHEALTHY_BASELINE" for row in case.get("findings", []))):
        raise ValueError("SDK headline is not supported by freshly checked equal, broken outputs")


def verify_wheel(path):
    path = Path(path)
    if path.is_symlink() or path.name != f"reviknot-{__version__}-py3-none-any.whl" or not path.is_file():
        raise ValueError("Download must be the current regular Python wheel")
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 2000 or sum(row.file_size for row in archive.infolist()) > 50_000_000:
            raise ValueError("Wheel exceeds archive size limits")
        for row in archive.infolist():
            if row.filename.startswith(("/", "\\")) or ".." in row.filename.replace("\\", "/").split("/"):
                raise ValueError("Wheel contains an unsafe archive path")
            text = archive.read(row).decode("utf-8", errors="ignore")
            public_evidence(text)
    return path


def verify_gate_bundle(folder):
    """Validate data and exact trusted checker source; never execute supplied tests."""
    from acv.scanner import _is_link_like
    from patchcourt.recording_export import GATE_TEST, PORTABLE_GATE_FILES
    from patchcourt.semantic import compare_messages
    folder = Path(folder)
    if _is_link_like(folder) or not folder.is_dir():
        raise ValueError("Gate bundle must be a regular exported directory")
    folder = folder.resolve()
    portable = set(PORTABLE_GATE_FILES)
    allowed = portable | {"report.json", "manifest.json", "report.md", "index.html", "regression-gate.zip"}
    found = set()
    for base, dirs, files in os.walk(folder, followlinks=False):
        retained = []
        for name in dirs:
            path = Path(base) / name
            relative = path.relative_to(folder).as_posix()
            if _is_link_like(path):
                raise ValueError("Gate bundle contains an unexpected directory or link")
            if relative in {"__pycache__", "_patchcourt_contract/__pycache__"}:
                continue  # Never read, execute or publish local bytecode caches.
            if relative != "_patchcourt_contract":
                raise ValueError("Gate bundle contains an unexpected directory or link")
            retained.append(name)
        dirs[:] = retained
        for name in files:
            path = Path(base) / name
            relative = path.relative_to(folder).as_posix()
            if _is_link_like(path) or relative not in allowed:
                raise ValueError("Gate bundle contains an unexpected file or link")
            found.add(relative)
        if len(found) > len(allowed):
            raise ValueError("Gate bundle exceeds its file limit")
    if not (portable | {"report.json", "manifest.json", "regression-gate.zip"}) <= found:
        raise ValueError("Gate bundle is incomplete")
    def bounded(name, limit=8_000_000):
        path = folder / name
        if path.stat().st_size > limit:
            raise ValueError("Gate file exceeds its size limit")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Gate file exceeds its size limit")
        return data
    files = {name: bounded(name, 1_000_000 if name.startswith("_patchcourt_contract/") else 8_000_000)
             for name in portable}
    proof = {name: bounded(name) for name in ("report.json", "manifest.json")}
    report, manifest = (strict_json(proof[name].decode("utf-8-sig")) for name in ("report.json", "manifest.json"))
    if (not isinstance(report, dict) or not isinstance(manifest, dict) or not report.get("run_id")
            or report["run_id"] != manifest.get("run_id") or digest(report) != manifest.get("report_sha256")):
        raise ValueError("Gate report integrity does not match its manifest")
    contract = strict_json(files["contract.json"].decode("utf-8-sig"))
    observed = strict_json(files["observed-candidate.json"].decode("utf-8-sig"))
    for item in (report, manifest, contract, observed):
        public_evidence(item)
    expected_keys = {"schema_version", "kind", "adapter", "captured_version", "request_id", "expected_input",
                     "observed_status", "runtime_files_sha256", "observed_candidate_file_sha256", "scope"}
    if (not isinstance(contract, dict) or set(contract) != expected_keys or contract.get("schema_version") != "1.0"
            or contract.get("kind") != "captured-boundary-regression-contract"
            or not isinstance(observed, list) or report.get("mode") != "recording-check"
            or not isinstance(report.get("cases"), list) or len(report["cases"]) != 1
            or not isinstance(report["cases"][0], dict) or not isinstance(report.get("regression_gate"), dict)
            or not isinstance(report.get("recording"), dict) or report.get("provider_requests") != 0
            or report["recording"].get("payload_redacted") is not False):
        raise ValueError("Gate input does not establish a supported captured-boundary export")
    case, gate = report["cases"][0], report.get("regression_gate", {})
    baseline = compare_messages(contract["expected_input"], contract["expected_input"])
    verdict = compare_messages(contract["expected_input"], observed)
    if (baseline["status"] != "PASS" or report.get("status") != verdict["status"]
            or case.get("status") != verdict["status"] or case.get("execution") is not False
            or digest(case.get("baseline")) != digest(contract["expected_input"])
            or digest(report.get("input")) != digest(contract["expected_input"])
            or digest(case.get("candidate")) != digest(observed)
            or digest(case.get("findings")) != digest(verdict["findings"])
            or digest(case.get("contracts")) != digest({"input": baseline, "baseline": baseline, "candidate": verdict, "difference": verdict})
            or contract.get("observed_status") != verdict["status"]
            or gate.get("status") != "EXPORTED" or gate.get("default_candidate_status") != verdict["status"]
            or gate.get("default_test_expected") != ("PASS" if verdict["status"] == "PASS" else "FAIL")
            or gate.get("standalone_standard_library") is not True):
        raise ValueError("Gate headline differs from fresh captured-input comparison")
    for key, recorded in (("adapter", "adapter"), ("captured_version", "version"), ("request_id", "request_id")):
        if contract.get(key) != report["recording"].get(recorded):
            raise ValueError("Gate identity differs from its report")
    runtime = contract["runtime_files_sha256"]
    runtime_names = {name for name in portable if name.startswith("_patchcourt_contract/")}
    if not isinstance(runtime, dict) or set(runtime) != runtime_names or runtime != gate.get("runtime_files_sha256"):
        raise ValueError("Gate runtime file allowlist differs")
    current = {"version_snapshot.py": ('__version__ = ' + repr(__version__) + '\n').encode("utf-8"),
               "LICENSE": (ROOT / "patchcourt/fixtures/PATCHCOURT-LICENSE").read_bytes()}
    current.update({name: (ROOT / "patchcourt" / name).read_bytes() for name in ("evidence.py", "semantic.py", "recording.py")})
    for name in runtime_names:
        data = files[name]
        if hashlib.sha256(data).hexdigest() != runtime[name]:
            raise ValueError("Gate checker source does not match its recorded hash")
        if data.decode("utf-8").replace("\r\n", "\n") != current[Path(name).name].decode("utf-8").replace("\r\n", "\n"):
            raise ValueError("Gate checker source differs from the current reviewed project source")
        public_evidence(data.decode("utf-8"))
    contract_sha = hashlib.sha256(files["contract.json"]).hexdigest()
    expected_test = GATE_TEST.replace("CONTRACT_SHA256", contract_sha)
    if (files["test_boundary_contract.py"].decode("utf-8").replace("\r\n", "\n") != expected_test.replace("\r\n", "\n")
            or gate.get("contract_file_sha256") != contract_sha
            or gate.get("test_file_sha256") != hashlib.sha256(files["test_boundary_contract.py"]).hexdigest()
            or contract.get("observed_candidate_file_sha256") != hashlib.sha256(files["observed-candidate.json"]).hexdigest()):
        raise ValueError("Gate test or captured fixture differs from the exact reviewed export")
    public_evidence(files["REGRESSION-GATE.md"].decode("utf-8"))
    archive = bounded("regression-gate.zip", 20_000_000)
    if gate.get("download_file") != "regression-gate.zip" or gate.get("archive_sha256") != hashlib.sha256(archive).hexdigest():
        raise ValueError("Gate archive differs from the verified report")
    import io
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        entries = zipped.infolist()
        if len(entries) != len(portable) or {row.filename for row in entries} != portable or sum(row.file_size for row in entries) > 20_000_000:
            raise ValueError("Gate archive does not match the portable file allowlist")
        for row in entries:
            if row.is_dir() or stat.S_ISLNK(row.external_attr >> 16) or row.flag_bits & 1 or zipped.read(row) != files[row.filename]:
                raise ValueError("Gate archive member differs from the reviewed files")
    return {"report": report, "files": files, "proof": proof, "archive": archive}


def _mcp_portal(bundle):
    """Render recorded MCP proof separately from model-inference playback."""
    report = bundle["report"]
    card = ('<article class="card" id="mcp-workflow" style="grid-column:1/-1;background:#eef2ff">'
            '<div class="eyebrow">03 / Use it from your coding agent</div>'
            '<h2>Check the captured boundary before the merge.</h2>'
            '<p>Four local MCP tools return exact finding paths, compare versions against the original input, '
            'and export a standard-library CI gate. Inspect a recorded official SDK client checking a two-tool refund draft: '
            'broken → fixed → deliberately corrupted, with CI exits <strong>1 → 0 → 1</strong>.</p>'
            '<p>This is saved stdio client evidence. Your editor chooses when to invoke the tools; this page does not connect an editor or start a live session.</p>'
            '<a href="mcp-workflow.html">Inspect the recorded MCP workflow →</a> · '
            '<a href="MCP.md">Read MCP setup →</a> · <a href="refund-example.zip" download>Download the refund example ↓</a></article>')
    rows = []
    for index, row in enumerate(report["workflow"], 1):
        result = row["result"]
        arguments = html.escape(json.dumps(row["arguments"], ensure_ascii=False, indent=2))
        paths = [finding.get("path", "") for finding in result.get("findings", [])]
        details = html.escape(result.get("direction") or ", ".join(paths) or "See the hash-bound result")
        rows.append('<tr><td>' + str(index) + '</td><td><code>' + html.escape(row["tool"]) + '</code>'
                    '<details><summary>Arguments</summary><pre>' + arguments + '</pre></details></td><td><b>'
                    + html.escape(result["status"]) + '</b></td><td>' + details + '</td></tr>')
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>ReviKnot — captured MCP workflow</title><style>body{margin:0;background:#f4f5ef;color:#172923;font:16px/1.65 system-ui,Arial}main{max-width:1100px;margin:auto;padding:30px}a{color:#087454}h1{font-size:clamp(32px,5vw,60px);line-height:1.1;letter-spacing:-2px}h2{font-size:25px}.note{color:#58695e}.proof{display:flex;gap:22px;flex-wrap:wrap;padding:20px;background:#e6f2e9;border:1px solid #d9dfd4;border-radius:10px}.proof b{display:block;font-size:28px}.proof span{font-size:13px}.card{background:white;padding:24px;margin:24px 0;border:1px solid #d9dfd4;border-radius:10px}table{width:100%;border-collapse:collapse;text-align:left;font-size:14px}td,th{padding:13px 10px;border-bottom:1px solid #e0e6dd;vertical-align:top}code,pre{font:13px/1.6 monospace;overflow-wrap:anywhere;white-space:pre-wrap}details{margin-top:7px}summary{cursor:pointer;color:#087454}.scroll{overflow:auto}footer{font-size:12px;color:#58695e}</style></head><body><main>
<a href="index.html">← ReviKnot judge demo</a><h1>A verification tool for<br>your coding agent.</h1>
<p class="note">Recorded official MCP SDK client over stdio. No live editor session or automatic trigger is claimed.</p>
<div class="proof"><div><b>4</b><span>Local MCP tools</span></div><div><b>6</b><span>Recorded tool calls</span></div><div><b>1 → 0 → 1</b><span>Broken / fixed / corrupt CI exits</span></div><div><b>0</b><span>Provider requests in this MCP check</span></div></div>
<section class="card"><h2>A refund draft with more to preserve.</h2><p>The controlled adapter handles two tool calls, nested policy booleans, Unicode, currency and a human approval requirement. One broken conversion loses tool calls. The reviewed candidate preserves the captured input. A corruption changes <code>opened: false</code> to <code>opened: 0</code>, and the checker rejects that semantic type change.</p><p>The unhealthy baseline remains <strong>NEEDS_REVIEW</strong>; the candidate contract passes independently. Equal broken outputs cannot earn compatibility.</p><p>This is local synthetic refund data. It does not execute a payment or establish an untested SDK defect.</p></section>
<section class="card"><h2>The actual recorded tool flow</h2><div class="scroll"><table><thead><tr><th>#</th><th>Tool</th><th>Result</th><th>Finding path or direction</th></tr></thead><tbody>WORKFLOW_ROWS</tbody></table></div></section>
<section class="card"><h2>Use it in your project</h2><p>Install ReviKnot with its optional MCP extra using Python 3.11+, then register <code>python -m reviknot mcp --workspace /absolute/project/path</code> in your MCP host. The base CLI remains Python 3.10+. The host initiates calls after the developer captures a boundary; the server does not poll your editor.</p><p><a href="MCP.md">Read complete installation and host setup →</a> · <a href="refund-example.zip" download>Download the example ↓</a></p><p>Viewing this receipt and running the exported standard-library gate need no API key. A new MCP session needs the optional SDK installed. Generating a repair with an NVIDIA model is a separate, explicitly requested live workflow.</p></section>
<section class="card"><h2>Inspect the evidence</h2><p><a href="evidence/mcp/mcp-workflow.json">Full receipt and file hashes →</a> · <a href="mcp-proof.zip" download>Download the complete recorded proof ↓</a> · <a href="evidence/mcp/regression-gate/regression-gate.zip" download>Download this captured CI gate ↓</a></p><p>SDK_VERSION_LABEL · ReviKnot VERSION_LABEL. Current source fingerprints and every included file are checked during export. Checksums detect changes; they do not independently authenticate a producer. Supplied Python files are not executed by the exporter or this page.</p></section>
<footer>Saved controlled execution evidence. MCP and model-inference proofs cover separate operations.</footer></main></body></html>'''
    if "MCP.zh-CN.md" in bundle["downloads"]:
        card = card.replace('Read MCP setup →</a>', 'Read MCP setup →</a> · <a href="MCP.zh-CN.md">简体中文指南 →</a>')
        page = page.replace('Read complete installation and host setup →</a>', 'Read complete installation and host setup →</a> · <a href="MCP.zh-CN.md">简体中文接入指南 →</a>')
    return card, page.replace("WORKFLOW_ROWS", "".join(rows)).replace("SDK_VERSION_LABEL", "Official MCP SDK " + html.escape(report["execution"]["mcp_sdk_version"])).replace("VERSION_LABEL", html.escape(__version__))


def package(live_folder, sdk_folder, output, *, wheel=None, source_url=None, gate_dir=None, mcp_evidence=None):
    live_folder, sdk_folder, output = Path(live_folder), Path(sdk_folder), Path(output)
    if output.exists() or output.with_name(output.name + ".zip").exists():
        raise ValueError("Refusing to overwrite an existing judge package")
    if source_url:
        url = urlsplit(source_url)
        if (url.scheme != "https" or url.hostname not in {"github.com", "gitlab.com", "bitbucket.org"}
                or url.username or url.password or url.port not in (None, 443)):
            raise ValueError("Source link must be a public HTTPS code-host URL")
    live, records = verify_workflow(live_folder.resolve(), "report.json")
    sdk = verified_report(sdk_folder)
    verify_sdk_report(sdk)
    wheel = verify_wheel(wheel) if wheel else None
    gate_bundle = verify_gate_bundle(gate_dir) if gate_dir is not None else None
    if mcp_evidence is not None:
        from scripts.mcp_evidence import verify_mcp_evidence
        mcp_bundle = verify_mcp_evidence(mcp_evidence)
    else:
        mcp_bundle = None
    evidence_files = ["report.json", "manifest.json"]
    evidence_files.extend(row["name"] + ".json" for row, _ in records)
    output.mkdir(parents=True, exist_ok=False)
    (output / "evidence" / "live").mkdir(parents=True)
    for name in evidence_files:
        shutil.copyfile(live_folder / name, output / "evidence" / "live" / name)
    for name in ("report.json", "manifest.json"):
        shutil.copyfile(sdk_folder / name, output / name)
    gate_card, mcp_card = "", ""
    if mcp_bundle:
        mcp_card, mcp_page = _mcp_portal(mcp_bundle)
        (output / "mcp-workflow.html").write_text(mcp_page, encoding="utf-8")
        for name, data in mcp_bundle["files"].items():
            target = output / "evidence/mcp" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for name, data in mcp_bundle["downloads"].items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for archive_name, entries in (("mcp-proof.zip", mcp_bundle["files"]), ("refund-example.zip", mcp_bundle["downloads"])):
            with zipfile.ZipFile(output / archive_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
    if gate_bundle:
        for name, data in gate_bundle["files"].items():
            path = output / "ci-gate" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for name, data in gate_bundle["proof"].items():
            path = output / "evidence" / "ci-gate" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (output / "ci-gate.zip").write_bytes(gate_bundle["archive"])
        status = html.escape(gate_bundle["report"]["status"])
        default = "intentionally fails" if status != "PASS" else "passes for the saved observation"
        gate_card = '<article class="card" id="ci-gate" style="grid-column:1/-1;background:#eaf4ec"><div class="eyebrow">03 / Bring your captured boundary into CI</div><h2>A regression test for the messages you actually captured.</h2><p>The saved candidate is <strong>' + status + '</strong>; the default test ' + default + '. Download the standalone checker and supply a fresh candidate trace or recording to check the same frozen input. No API key or pip install is required. The gate checks captured data and does not execute a future SDK.</p><p><code>python -m unittest discover -s ci-gate -p test_boundary_contract.py</code></p><a href="ci-gate.zip" download>Download complete CI gate ↓</a> · <a href="evidence/ci-gate/report.json">Inspect the captured-boundary evidence →</a></article>'
    shutil.copyfile(ROOT / "patchcourt/web/index.html", output / "sdk-upgrade.html")
    replay = (ROOT / "patchcourt/web/live.html").read_text(encoding="utf-8")
    embedded = json.dumps(live, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    replay = replay.replace("<script>", '<script id="recorded-data" type="application/json">' + embedded + "</script>\n<script>", 1)
    (output / "repair.html").write_text(replay, encoding="utf-8")
    provider = html.escape(live["provider"])
    model = html.escape(live["model"])
    checks = live["verification"]["checks"]
    passed = sum(c["status"] == "PASS" for c in checks)
    answer = html.escape(str(live["task"]["answer"]["inventory_value"]))
    scope = ("Recorded NVIDIA model inference on Nebius Token Factory."
             if live["provider"] == "nebius" else "Development run. Nebius/NVIDIA competition runtime is not established by this recording.")
    source = '<a href="' + html.escape(source_url, quote=True) + '">Source code ↗</a>' if source_url else ""
    download = ""
    if wheel:
        wheel = Path(wheel)
        shutil.copyfile(wheel, output / wheel.name)
        download = '<a class="secondary" href="' + html.escape(wheel.name, quote=True) + '" download>Download Python build ↓</a>'
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="description" content="Catch silent agent SDK regressions with independently checked repair evidence."><title>ReviKnot — inspect the repair</title>
<style>:root{--ink:#172923;--muted:#64736c;--paper:#f4f5ef;--line:#d9dfd4;--green:#087454}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,Arial}main,header,footer{max-width:1180px;margin:auto;padding:22px 30px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);gap:20px}.brand{font-size:23px;font-weight:800;letter-spacing:-1px}.brand span{color:var(--green)}nav{display:flex;gap:24px;font-size:13px}a{color:inherit;text-decoration:none}a:hover{text-decoration:underline}a:focus-visible{outline:3px solid var(--green);outline-offset:5px}.hero{padding:60px 0 34px;max-width:930px}.eyebrow{font:11px monospace;letter-spacing:1.8px;color:var(--green);text-transform:uppercase}h1{font-size:clamp(39px,5.2vw,66px);letter-spacing:-2.5px;line-height:1.06;margin:20px 0 24px;font-weight:700}h1 span{color:var(--green)}p{color:var(--muted)}.hero p{max-width:760px;font-size:17px}.actions{display:flex;flex-wrap:wrap;gap:12px;margin:29px 0 0}.primary,.secondary{display:inline-block;padding:13px 21px;border-radius:7px;font-size:14px;font-weight:650}.primary{background:var(--ink);color:white}.secondary{border:1px solid var(--line);background:white}.proof{border:1px solid var(--line);border-radius:11px;background:white;margin:14px 0 35px;overflow:hidden}.proof-top{padding:19px 23px;background:#eef5ee;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:18px;font:12px monospace}.stats{display:grid;grid-template-columns:repeat(4,1fr)}.stat{padding:24px;border-right:1px solid var(--line)}.stat:last-child{border:0}.stat b{display:block;font-size:34px;line-height:1.2;margin-bottom:10px;color:var(--green)}.stat span{font-size:12px;color:var(--muted)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.card{padding:25px;border:1px solid var(--line);border-radius:10px;background:#fff}.card h2{font-size:21px;margin:9px 0}.card p{font-size:14px}.card a{font-size:13px;font-weight:650;color:var(--green)}.scope{border-top:1px solid var(--line);padding-top:22px;margin-top:35px;font-size:12px;max-width:1000px}footer{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;gap:20px;padding-bottom:30px}code{font:12px monospace;overflow-wrap:anywhere}@media(max-width:700px){main,header,footer{padding-left:20px;padding-right:20px}header{align-items:flex-start}nav{gap:12px;flex-wrap:wrap;justify-content:end}.hero{padding-top:38px}h1{letter-spacing:-1.5px}.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}.stat:nth-child(2){border-right:0}.stat:nth-child(-n+2){border-bottom:1px solid var(--line)}.proof-top,footer{flex-direction:column;gap:6px}}</style></head><body>
<header><div class="brand">Revi<span>Knot</span></div><nav><a href="repair.html">Repair evidence</a><a href="sdk-upgrade.html">SDK inspector</a>SOURCE_LINK</nav></header>
<main><section class="hero"><div class="eyebrow">AI Agent Compatibility Guardian</div><h1>The tools ran.<br><span>The next request forgot them.</span></h1><p>An SDK can silently drop tool calls after they execute. ReviKnot exposes the missing semantics, challenges a model-proposed repair, and verifies that the task recovers.</p><div class="actions"><a class="primary" href="repair.html">Replay the verified repair →</a><a class="secondary" href="sdk-upgrade.html">Inspect a real SDK upgrade →</a>DOWNLOAD_LINK</div></section>
<section class="proof" aria-label="Recorded execution results"><div class="proof-top"><span>PROVIDER_LABEL / MODEL_LABEL</span><span>Recorded evidence · no API key needed to replay</span></div><div class="stats"><div class="stat"><b>CHECKS_LABEL</b><span>Independent repair checks passed</span></div><div class="stat"><b>Rejected</b><span>Deliberately corrupted repair</span></div><div class="stat"><b>ANSWER_LABEL</b><span>Verified inventory task value</span></div><div class="stat"><b>REQUESTS_LABEL</b><span>Model requests in the saved run</span></div></div></section>
<div class="grid"><article class="card"><div class="eyebrow">01 / Detection</div><h2>Equal broken outputs do not mean compatible.</h2><p>Unmodified NVIDIA SDK releases 1.4.3 and 1.5.0 run independently. Each output is checked against the original input, so an already broken baseline remains visible.</p><a href="sdk-upgrade.html">Open recorded version comparison →</a></article><article class="card"><div class="eyebrow">02 / Independent verification</div><h2>The model cannot approve its own repair.</h2><p>A bounded field mapping faces controls for nested data, multiple calls and legacy behavior. A damaged repair must fail before the actual tool conversation can earn a verified result.</p><a href="evidence/live/report.json">Read complete model and task evidence →</a></article></div>
<p class="scope">SCOPE_LABEL Playback uses saved real execution data and sends no new inference requests. The adapter harness uses reviewed historical source and inert message types; the inventory tools are controlled local fixtures. This is not a general code sandbox. Checksums detect changes and do not independently authenticate a producer. Historical known SDK defects are credited in the source. Submission eligibility and final form completion require the separate checklist.</p>
<p class="scope">Run the installed project: <code>python -m reviknot demo --output outputs/demo</code><br>Serve this static package: <code>python -m http.server 8765 --bind 127.0.0.1</code></p></main>
<footer><span>ReviKnot · VERSION_LABEL · inspect the evidence</span><span>Saved run: RUN_LABEL</span></footer></body></html>"""
    replacements = {"SOURCE_LINK": source, "DOWNLOAD_LINK": download, "PROVIDER_LABEL": provider, "MODEL_LABEL": model,
                    "CHECKS_LABEL": f"{passed}/{len(checks)}", "ANSWER_LABEL": answer, "REQUESTS_LABEL": str(len(live["requests"])),
                    "SCOPE_LABEL": html.escape(scope), "VERSION_LABEL": __version__, "RUN_LABEL": html.escape(live["run_id"])}
    if gate_card or mcp_card:
        if mcp_card:
            gate_card = gate_card.replace("03 / Bring", "04 / Bring")
        page = page.replace('</article></div>\n<p class="scope">', '</article>' + mcp_card + gate_card + '</div>\n<p class="scope">', 1)
    for key, value in replacements.items():
        page = page.replace(key, value)
    (output / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(ROOT / "LICENSE", output / "LICENSE")
    (output / "launch_demo.py").write_text(LAUNCHER, encoding="utf-8")
    (output / "Start-Judge-Demo.cmd").write_text(WINDOWS_LAUNCHER, encoding="ascii")
    (output / "START-HERE.txt").write_text("ReviKnot judge demo\n\nWindows: double-click Start-Judge-Demo.cmd.\nAny platform with Python 3: run python launch_demo.py.\nThe launcher serves only this exported folder on 127.0.0.1 with an available local port and opens your browser. Nothing is installed. Press Ctrl+C to close the server.\n\nRecorded repair playback and the SDK inspector need no API key or inference access. The replay is recorded execution evidence, not a new model call.\n", encoding="utf-8")
    if mcp_bundle:
        with (output / "START-HERE.txt").open("a", encoding="utf-8") as stream:
            stream.write("\nThe MCP card shows a saved official-client stdio verification, not a live editor session. Read MCP.md for optional Python 3.11+ setup. Download the refund example or recorded proof from that card; no API key is needed to inspect them.\n")
    hashes = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*") if p.is_file()}
    (output / "package-manifest.json").write_text(json.dumps({"version": __version__, "live_run_id": live["run_id"],
        "provider": live["provider"], "model": live["model"], "files": hashes,
        "replay_only": True, "new_provider_requests": 0,
        "mcp_proof": mcp_bundle["summary"] if mcp_bundle else None}, indent=2) + "\n", encoding="utf-8")
    archive = output.with_name(output.name + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in output.rglob("*"):
            if path.is_file():
                zipped.write(path, path.relative_to(output).as_posix())
    return {"status": "PACKAGED", "directory": str(output.resolve()), "archive": str(archive.resolve()),
            "provider": live["provider"], "replay_only": True, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-report", type=Path, required=True)
    parser.add_argument("--sdk-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--source-url")
    parser.add_argument("--gate-dir", type=Path, help="Optional current captured-boundary export; its exact checker is verified without executing it")
    parser.add_argument("--mcp-evidence", type=Path, help="Optional saved official-client MCP proof; file hashes, tool results and trusted source are verified without executing supplied Python")
    args = parser.parse_args()
    print(json.dumps(package(args.live_report, args.sdk_report, args.output, wheel=args.wheel, source_url=args.source_url, gate_dir=args.gate_dir, mcp_evidence=args.mcp_evidence)))


if __name__ == "__main__":
    main()
