"""Practical CLI, offline by default. Exit 1 means regression, 2 means uncertainty."""
import argparse
from contextlib import nullcontext
import json
import sys
from pathlib import Path
from .evidence import read_json, write_json


def _live_options(parser):
    parser.add_argument('--max-model-requests',type=int,default=16,help='Per-run model dispatch ceiling; the persistent ledger can impose a smaller remaining allowance')
    parser.add_argument('--max-tool-turns',type=int,default=8,help='Maximum model/tool conversation turns')
    parser.add_argument('--max-repair-attempts',type=int,default=3,help='Maximum model proposals; every candidate still requires independent verification')
    parser.add_argument('--token-reservation-limit',type=int,default=400000,help='Per-run model UTF-8 payload bytes plus output reservations; not exact tokens or billing')
    parser.add_argument('--max-output-tokens',type=int,help='Per-request output ceiling; defaults to 2048 for Nebius, 4096 otherwise; model/account capacity still requires validation')


def _workflow_options(args):
    return {name:getattr(args,name) for name in ('max_model_requests','max_tool_turns','max_repair_attempts','token_reservation_limit','max_output_tokens')}


def _saved_or_new_budget(path):
    from .budget import RequestBudget
    return RequestBudget.from_existing(path) if Path(path).exists() else RequestBudget(path)


def _boundary_input(path):
    if path is None:
        return None
    from .boundary_run import INPUT_LIMIT
    if Path(path).stat().st_size > INPUT_LIMIT:
        raise ValueError("Boundary input exceeds 128 KB")
    value = read_json(path)
    if not isinstance(value, list):
        raise ValueError("Explicit boundary input must be a message-array JSON; null does not select the demo fixture")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(prog="reviknot", description="Catch silent AI agent compatibility regressions with executable evidence.")
    from . import __version__
    parser.add_argument("--version", action="version", version="ReviKnot " + __version__)
    parser.add_argument("--env-file", help="Explicit local credential file; only supported API variables are loaded")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="Check all tools, generate MCP configuration and run the quickstart")
    setup.add_argument("--workspace", default=".")
    setup.add_argument("--client", choices=("none", "codex", "cursor", "claude-code"), default="none")
    setup.add_argument("--open", action="store_true", help="Open the local demo after setup")
    doctor = commands.add_parser("doctor", help="Check installation and discover all four tools through real MCP stdio")
    doctor.add_argument("--workspace", default=".")
    demo = commands.add_parser("demo", help="Execute pinned source cases, repairs, controls and export the dashboard")
    demo.add_argument("--output", default="outputs/reviknot")
    demo.add_argument("--knowledge-dir")
    check = commands.add_parser("check", help="Compare two captured message-array JSON files")
    check.add_argument("baseline"); check.add_argument("candidate")
    check.add_argument("--output", default="outputs/check")
    check.add_argument("--input", help="Original message-array JSON; also check that each trace preserves its semantics")
    captured = commands.add_parser("check-recording", help="Check one opt-in captured transaction and export a portable regression gate; no SDK execution")
    captured.add_argument("recording", help="BoundaryRecorder schema 1.0 JSON")
    captured.add_argument("--request-id", help="Required when more than one adapter transaction was captured")
    captured.add_argument("--output", required=True, help="New evidence directory; prior output is never overwritten")
    mcp = commands.add_parser("mcp", help="Expose local boundary verification and regression-gate tools over MCP stdio; all four tools included in the default installation")
    mcp.add_argument("--workspace", required=True, help="Existing root directory; tool file paths must be relative to this workspace")
    mcp.add_argument("--max-file-bytes", type=int, default=8_000_000, help="Maximum JSON file size per tool input (1..64000000 bytes)")
    mcp.add_argument("--max-findings", type=int, default=100, help="Maximum returned findings per comparison (1..10000); total and truncation remain explicit")
    mcp.add_argument("--max-finding-chars", type=int, default=2048, help="Maximum diagnostic text preview per field (64..65536 characters); original size and hash remain explicit")
    boundary = commands.add_parser("boundary-run", help="Execute two reviewed NVIDIA serializer variants; no provider calls")
    boundary.add_argument("--baseline", choices=("upstream", "reviewed-patch"), default="upstream",
                          help="Earlier implementation; defaults to the known broken upstream")
    boundary.add_argument("--candidate", choices=("upstream", "reviewed-patch"), default="reviewed-patch",
                          help="Implementation to test; defaults to the reviewed repair")
    boundary.add_argument("--input", help="Text/tool-call message-array JSON; defaults to two-tool regression fixture")
    boundary.add_argument("--sdk-root", help="Trusted installed NVIDIA 1.4.3 dependency target; otherwise use pinned source with inert classes")
    boundary.add_argument("--output", required=True, help="New evidence directory; existing directories are never overwritten")
    upgrade = commands.add_parser("upgrade-run", help="Inspect a repository and execute two real, reviewed NVIDIA SDK releases")
    upgrade.add_argument("repository", help="Read-only source discovery; repository code is never imported")
    upgrade.add_argument("--from-version", choices=("1.4.3", "1.5.0"), required=True)
    upgrade.add_argument("--to-version", choices=("1.4.3", "1.5.0"), required=True)
    upgrade.add_argument("--environment-dir", required=True, help="Dedicated dependency targets, verified before every execution")
    upgrade.add_argument("--prepare", action="store_true", help="Opt into installing official, wheel-only dependencies in new targets")
    upgrade.add_argument("--wheelhouse", help="With --prepare, install offline from this trusted wheel directory")
    upgrade.add_argument("--input", help="Text/tool-call message-array JSON; otherwise use the deterministic two-tool task")
    upgrade.add_argument("--output", required=True, help="New evidence directory")
    inspect = commands.add_parser("inspect", help="Find candidate adapter boundaries without executing repository code")
    inspect.add_argument("repository"); inspect.add_argument("--dependency", required=True)
    inspect.add_argument("--from-version", required=True); inspect.add_argument("--to-version", required=True)
    inspect.add_argument("--output", default="outputs/inspection.json")
    bench = commands.add_parser("benchmark", help="Record every scheduled ablation outcome")
    bench.add_argument("--output", default="outputs/benchmark")
    bench.add_argument("--provider", choices=("offline", "glm"), default="offline", help="glm opts into three bounded inference requests and one Tavily search")
    verify = commands.add_parser("verify", help="Check exported report integrity; does not certify truth")
    verify.add_argument("directory")
    feedback = commands.add_parser("feedback", help="Build a reviewable feedback draft from lab evidence; never infer platform defects")
    feedback.add_argument("run_directory")
    feedback.add_argument("--output", default="outputs/feedback")
    feedback.add_argument("--max-chars", type=int, default=2000)
    lab = commands.add_parser("lab", help="Run bounded real Nebius/Tavily trials; missing keys produce BLOCKED evidence")
    lab.add_argument("--output", default="outputs/lab"); lab.add_argument("--model"); lab.add_argument("--trials", type=int, default=3)
    reasoning = commands.add_parser("reason", help="Ask a real provider for declarative tests and a repair proposal")
    reasoning.add_argument("source"); reasoning.add_argument("evidence")
    reasoning.add_argument("--model"); reasoning.add_argument("--tavily", action="store_true"); reasoning.add_argument("--output", default="outputs/reasoning.json")
    reasoning.add_argument("--provider", choices=("nebius", "glm", "deepseek"), default="nebius")
    reasoning.add_argument("--max-output-tokens", type=int, default=8192, help="Maximum answer length; the selected model may impose a lower limit")
    source_review = commands.add_parser("review-source", help="Review every scanned source fragment in bounded chunks, with an explicit coverage record")
    source_review.add_argument("source", help="A source file or a project directory; code is never executed")
    source_review.add_argument("--provider", choices=("nebius", "deepseek", "glm"), default="deepseek")
    source_review.add_argument("--model", help="Exact model ID; Nebius requires an NVIDIA Nemotron model")
    source_review.add_argument("--context-tokens", type=int, default=100000, help="Per-request window budget; UTF-8 bytes conservatively bound input tokens, including prompt overhead")
    source_review.add_argument("--max-output-tokens", type=int, default=8192, help="Answer ceiling, configurable up to the application/provider allowance")
    source_review.add_argument("--max-chunks", type=int, default=20, help="Refuse a larger plan before sending requests")
    source_review.add_argument("--max-file-bytes", type=int, default=8000000, help="Explicit source-file size limit; skipped files remain disclosed")
    source_review.add_argument("--budget", help="Persistent request ledger; required unless --dry-run is selected")
    source_review.add_argument("--dry-run", action="store_true", help="Write the complete source plan without credentials, discovery or inference")
    source_review.add_argument("--no-compact", action="store_true", help="Keep duplicate findings in the combined summary; per-chunk evidence is always retained")
    source_review.add_argument("--output", required=True, help="New report directory; prior evidence is never overwritten")
    serve = commands.add_parser("serve", help="Serve only exported static evidence on loopback; no code-execution endpoint")
    serve.add_argument("directory", nargs="?", default="outputs/reviknot"); serve.add_argument("--port", type=int, default=8765)
    live = commands.add_parser("live", help="Run a bounded provider repair and fixture-tool workflow")
    live.add_argument("--output", required=True)
    live.add_argument("--provider", choices=("glm", "deepseek", "nebius"), default="glm")
    live.add_argument("--model", help="Explicit NVIDIA Nemotron ID for Nebius; fixed models on other providers")
    live.add_argument("--tavily", action="store_true", help="Supply official documentation to the repair proposal")
    live.add_argument("--knowledge-dir", help="Reuse exact verified mapping after all checks rerun; task still makes real API calls")
    live.add_argument('--budget',help='Optional persistent request ledger; existing saved limits are read exactly, never silently increased')
    _live_options(live)
    live_demo = commands.add_parser("live-demo", help="Loopback-only interactive provider workbench with explicit startup run limits")
    live_demo.add_argument("--output", default="outputs/live-demo"); live_demo.add_argument("--port",type=int,default=8780)
    live_demo.add_argument("--provider", choices=("glm", "deepseek", "nebius"), default="glm")
    live_demo.add_argument("--model")
    live_demo.add_argument("--tavily", action="store_true")
    live_demo.add_argument("--knowledge-dir", help="Save verified mappings and reuse them only after fresh independent checks")
    live_demo.add_argument('--budget',help='Optional persistent ledger shared by this server; saved limits remain authoritative')
    live_demo.add_argument('--max-runs',type=int,default=0,help='Optional server run ceiling; 0 (default) allows unlimited user-started runs; a supplied persistent ledger is still respected')
    _live_options(live_demo)
    budget_command=commands.add_parser('budget',help='Inspect a saved request ledger, or explicitly adjust its limits with an audit reason; no requests are made')
    budget_command.add_argument('ledger')
    budget_command.add_argument('--model-calls',type=int)
    budget_command.add_argument('--searches',type=int)
    budget_command.add_argument('--discovery-calls',type=int)
    budget_command.add_argument('--reason',help='Required for an explicit limit adjustment; prior reservations are never reset')
    args = parser.parse_args(argv)
    try:
        if args.command in {"setup", "doctor"}:
            from reviknot.setup import setup_workspace, doctor
            if args.command == "setup":
                setup_workspace(args.workspace, client=args.client, open_demo=args.open)
            else:
                print(json.dumps(doctor(args.workspace), ensure_ascii=False, indent=2))
            return 0
        if args.command == "mcp":
            if args.env_file:
                raise ValueError("MCP does not load credential files; omit --env-file")
            from .mcp_server import serve
            return serve(args.workspace, max_file_bytes=args.max_file_bytes, max_findings=args.max_findings,
                         max_finding_chars=args.max_finding_chars)
        if args.env_file:
            from .credentials import load_local_credentials
            load_local_credentials(args.env_file)
        if args.command=='budget':
            from .budget import RequestBudget
            changes={name:getattr(args,name) for name in ('model_calls','searches','discovery_calls') if getattr(args,name) is not None}
            if bool(changes)!=bool(args.reason):
                raise ValueError('Changing saved limits requires both an explicit limit and --reason')
            budget=RequestBudget.from_existing(args.ledger)
            if changes:
                budget.adjust_limits(**changes,reason=args.reason)
            counts={kind:sum(row['kind']==kind for row in budget.state['reservations']) for kind in budget.limits}
            print(json.dumps({'limits':budget.limits,'reservations':counts,
                'limit_adjustments':budget.state.get('limit_adjustments',[]),'provider_requests':0}))
            return 0
        if args.command == "demo":
            from .runner import demo
            report = demo(args.output, args.knowledge_dir)
            print(json.dumps({"output": str(Path(args.output).resolve()), "summary": report["summary"], "live_inference": False}))
            return 0 if all(c.get("expected_status", "FAIL") == c["status"] for c in report["cases"]) and all(c.get("repair", {}).get("status", "VERIFIED") == "VERIFIED" for c in report["cases"]) else 1
        if args.command == "check":
            from .sentinel import check_trace_pair
            from .runner import make_report, export_report
            original = {"original_input": read_json(args.input)} if args.input else {}
            case = check_trace_pair(read_json(args.baseline), read_json(args.candidate), **original)
            report = make_report([case])
            if args.input:
                report["input"] = original["original_input"]
            export_report(report, args.output)
            print(case["status"])
            return {"PASS": 0, "FAIL": 1}.get(case["status"], 2)
        if args.command == "check-recording":
            from .recording_export import check_recording
            report = check_recording(args.recording, args.output, args.request_id)
            print(json.dumps({"status": report["status"], "output": str(Path(args.output).resolve()),
                              "regression_gate": report["regression_gate"]["status"], "provider_requests": 0}))
            return {"PASS": 0, "FAIL": 1}.get(report["status"], 2)
        if args.command == "boundary-run":
            from .boundary_run import run_boundary
            report = run_boundary(args.output, baseline=args.baseline, candidate=args.candidate,
                                  messages=_boundary_input(args.input), sdk_root=args.sdk_root)
            case = next(iter(report.get("cases", [])), {})
            contracts = case.get("contracts", {})
            print(json.dumps({"status": report["status"], "output": str(Path(args.output).resolve()), "provider_requests": 0,
                              "baseline_variant": args.baseline, "candidate_variant": args.candidate,
                              "baseline_contract": contracts.get("baseline", {}).get("status"),
                              "candidate_contract": contracts.get("candidate", {}).get("status"),
                              "difference_status": contracts.get("difference", {}).get("status"),
                              "direction": case.get("direction")}))
            return {"PASS": 0, "FAIL": 1}.get(report["status"], 2)
        if args.command == "upgrade-run":
            from .upgrade_run import run_upgrade
            report = run_upgrade(args.repository, args.output, baseline=args.from_version, candidate=args.to_version,
                                 environment_dir=args.environment_dir, prepare=args.prepare, wheelhouse=args.wheelhouse,
                                 messages=_boundary_input(args.input))
            print(json.dumps({"status": report["status"], "output": str(Path(args.output).resolve()), "provider_requests": 0}))
            return {"PASS": 0, "FAIL": 1}.get(report["status"], 2)
        if args.command == "inspect":
            from .sentinel import inspect_repository
            result = inspect_repository(args.repository, args.dependency, args.from_version, args.to_version)
            write_json(args.output, result)
            print("NEEDS_REVIEW: source boundaries recorded; execute and compare traces for a verdict")
            return 2
        if args.command == "benchmark":
            if args.provider == "glm":
                from .evaluation import evaluate
                result = evaluate(args.output)
            else:
                from .runner import benchmark
                result = benchmark(args.output)
            print(json.dumps(result["metrics"]))
            return 2 if result.get("status") == "PARTIAL" else 0
        if args.command == "verify":
            from .evidence import digest
            root = Path(args.directory)
            report, manifest = read_json(root / "report.json"), read_json(root / "manifest.json")
            valid = (isinstance(report, dict) and isinstance(manifest, dict)
                     and isinstance(report.get("run_id"), str) and bool(report["run_id"].strip())
                     and report["run_id"] == manifest.get("run_id")
                     and digest(report) == manifest.get("report_sha256"))
            print("PASS: report integrity matches; provenance is not authenticated" if valid else "FAIL: report integrity mismatch")
            return 0 if valid else 1
        if args.command == "feedback":
            from .feedback import render_feedback
            result = render_feedback(args.run_directory, args.output, args.max_chars)
            print(json.dumps({"status": result["status"], "output": args.output}))
            return 2 if result["status"] == "BLOCKED" else 0
        if args.command == "lab":
            from .lab import run_lab
            result = run_lab(args.output, model=args.model, trials=args.trials)
            print(json.dumps({"status": result["status"], "output": args.output}))
            return {"PASS": 0, "FAIL": 1}.get(result["status"], 2)
        if args.command == "reason":
            from .reasoning import run_reasoning
            source = Path(args.source)
            if source.stat().st_size > 60_000:
                raise ValueError("Reasoning source is limited to 60 KB; pass only the relevant boundary")
            result = run_reasoning(source.read_text(encoding="utf-8"), read_json(args.evidence), use_tavily=args.tavily, model=args.model, provider=args.provider, max_output_tokens=args.max_output_tokens)
            write_json(args.output, result)
            print(json.dumps({"status": result["status"], "output": args.output}))
            return {"PASS": 0, "FAIL": 1}.get(result["status"], 2)
        if args.command == "review-source":
            from .source_review import run_source_review
            if not args.dry_run and not args.budget:
                raise ValueError("review-source requires --budget for paid requests; use --dry-run to plan without API access")
            options = dict(provider=args.provider, model=args.model, context_tokens=args.context_tokens,
                           max_output_tokens=args.max_output_tokens, max_chunks=args.max_chunks,
                           max_file_bytes=args.max_file_bytes, dry_run=args.dry_run, compact=not args.no_compact)
            if args.budget:
                budget = _saved_or_new_budget(args.budget)
                with budget.applied():
                    result = run_source_review(args.source, args.output, request_budget=budget, **options)
            else:
                result = run_source_review(args.source, args.output, **options)
            print(json.dumps({"status": result["status"], "output": str(Path(args.output).resolve()),
                              "scope": "Coverage of scanned source only; model suggestions do not establish verified defects"}))
            return 0 if result["status"] in {"COMPLETE", "PLANNED"} else 2
        if args.command == "serve":
            return serve_static(args.directory, args.port)
        if args.command == "live":
            from .live_workflow import run_live_workflow
            context=_saved_or_new_budget(args.budget).applied() if args.budget else nullcontext()
            with context:
                result=run_live_workflow(args.output,knowledge_dir=args.knowledge_dir,provider=args.provider,model=args.model,use_tavily=args.tavily,**_workflow_options(args))
            print(json.dumps({"status":result['status'],"output":args.output,"tokens":result['total_reported_tokens']}))
            return {"PASS": 0, "FAIL": 1}.get(result["status"], 2)
        if args.command == "live-demo":
            from .live_demo import serve_live_demo
            serve_live_demo(args.output,args.port,provider=args.provider,model=args.model,use_tavily=args.tavily,
                            knowledge_dir=args.knowledge_dir,budget_path=args.budget,max_runs=args.max_runs,**_workflow_options(args))
            return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        if args.command == "mcp":
            from .mcp_server import bounded_error
            limit = args.max_finding_chars if 64 <= args.max_finding_chars <= 65536 else 2048
            print("ReviKnot MCP: " + bounded_error(str(exc), limit), file=sys.stderr)
            return 2
        from .evidence import sanitize
        print("ReviKnot: " + sanitize(str(exc)), file=sys.stderr)
        return 2


def serve_static(directory, port, *, open_browser=False):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlsplit
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Choose a port from 0 to 65535; 0 selects an available local port")
    root = Path(directory).resolve()
    if not (root / "index.html").is_file() or not (root / "report.json").is_file():
        raise ValueError("Run reviknot demo first, or point serve at an exported report")
    # Explicit file allowlist; no directory traversal, source browsing, symlink reads or POSTs.
    allowed = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"), "/report.json": ("report.json", "application/json"), "/report.md": ("report.md", "text/plain; charset=utf-8")}
    allowed.update({"/contract.json": ("contract.json", "application/json"),
                    "/REGRESSION-GATE.md": ("REGRESSION-GATE.md", "text/plain; charset=utf-8"),
                    "/test_boundary_contract.py": ("test_boundary_contract.py", "text/plain; charset=utf-8"),
                    "/regression-gate.zip": ("regression-gate.zip", "application/zip")})
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host", "").lower() not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self.send_error(403); return
            item = allowed.get(urlsplit(self.path).path)
            if not item:
                self.send_error(404); return
            path = root / item[0]
            if path.is_symlink() or not path.is_file() or path.resolve().parent != root or path.stat().st_size > 10_000_000:
                self.send_error(404); return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", item[1]); self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers(); self.wfile.write(data)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    print(f"ReviKnot evidence viewer: {url}", flush=True)
    try:
        if open_browser:
            import webbrowser
            try:
                webbrowser.open(url)
            except (OSError, webbrowser.Error):
                print("Open the printed address in your browser.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
