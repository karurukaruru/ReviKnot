"""Optional official-SDK MCP tools for local captured-boundary verification.

No provider client, credential loader, project import or subprocess is used by
these tools. The server runs on stdio; the host chooses when to call a tool.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import sys

from .evidence import canonical, digest, strict_json, validate_shape
from .recording import select_recording, validate_recording
from .semantic import compare_messages


class WorkspaceError(ValueError):
    """A safe, actionable local-tool error, with no payload contents."""


def _bounded_text(value, limit):
    if len(value) <= limit:
        return value, None
    return value[:limit - 1] + "…", {
        "truncated": True, "characters": len(value),
        "sha256": hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest(),
    }


def bounded_error(value, limit=2048):
    """Bound error previews while retaining explicit original-size/hash data."""
    preview, details = _bounded_text(value, limit)
    if details is None:
        return preview
    return (preview + " [truncated; original_characters=" + str(details["characters"])
            + "; sha256=" + details["sha256"] + "]")


_PRIVATE_PARTS = {".git", ".ssh", ".aws", ".azure", ".config", ".kube", ".gnupg",
                  "node_modules", ".venv", ".venv-dev", ".venv-mcp", "__pycache__"}
_PRIVATE_NAMES = {"credentials", "credentials.json", "credential.json", "secrets.json", "secret.json",
                  "token.json", "tokens.json", "cookies.json", "id_rsa", "id_ed25519",
                  "config.json", ".npmrc", ".pypirc", ".netrc", "新建 文本文档.txt"}
_SENSITIVE_FIELD = re.compile(r"^(?:authorization|apikey|secret|clientsecret|password|accesstoken|refreshtoken|token|cookie|setcookie|privatekey|awsaccesskeyid|awssecretaccesskey)$")
_CREDENTIAL = re.compile(r"\b(?:sk-|tvly-)[A-Za-z0-9_-]{8,}|(?i:bearer\s+[A-Za-z0-9._~+/-]{6,})|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")


def _public_payload(value):
    """Reject recognizable credentials without consulting environment secrets."""
    validate_shape(value)
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = re.sub(r"[^a-z]", "", key.lower())
                if _SENSITIVE_FIELD.fullmatch(normalized) and child not in (None, "", "[REDACTED]", "Bearer [REDACTED]"):
                    raise WorkspaceError("Credential-bearing JSON is unavailable; capture non-sensitive fixture data first")
                pending.append(key)
                pending.append(child)
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str) and _CREDENTIAL.search(item):
            raise WorkspaceError("Credential-shaped JSON content is unavailable; value suppressed")
        elif isinstance(item, str) and item.lstrip().startswith(("{", "[")):
            # Tool argument/result payloads commonly contain JSON encoded in a
            # string. Inspect that form too instead of exposing a credential
            # merely because it was serialized one extra time.
            try:
                embedded = strict_json(item)
            except ValueError:
                continue
            pending.append(embedded)


def _link_like(path):
    metadata = path.lstat()
    return stat.S_ISLNK(metadata.st_mode) or bool(getattr(metadata, "st_file_attributes", 0) & 0x400)


class Workspace:
    """Bounded JSON files and new export folders in one explicitly chosen root."""

    def __init__(self, root, *, max_file_bytes=8_000_000, max_findings=100, max_finding_chars=2048):
        if type(max_file_bytes) is not int or not 1 <= max_file_bytes <= 64_000_000:
            raise WorkspaceError("max_file_bytes must be an integer in 1..64000000")
        if type(max_findings) is not int or not 1 <= max_findings <= 10000:
            raise WorkspaceError("max_findings must be an integer in 1..10000")
        if type(max_finding_chars) is not int or not 64 <= max_finding_chars <= 65536:
            raise WorkspaceError("max_finding_chars must be an integer in 64..65536")
        absolute = Path(root).absolute()
        if not absolute.is_dir():
            raise WorkspaceError("Workspace must be an existing directory")
        for part in (absolute, *absolute.parents):
            if _link_like(part):
                raise WorkspaceError("Workspace paths cannot contain symlinks or reparse points")
        self.root = absolute.resolve()
        self.max_file_bytes, self.max_findings = max_file_bytes, max_findings
        self.max_finding_chars = max_finding_chars

    def path(self, value, *, file=False, new_directory=False):
        if not isinstance(value, str) or not value or len(value) > 2048:
            raise WorkspaceError("Use a nonempty workspace-relative path of at most 2048 characters")
        if any(ord(char) < 32 for char in value) or ":" in value:
            raise WorkspaceError("Control characters, drive paths and alternate data streams are unavailable")
        portable = value.replace("\\", "/")
        supplied = Path(portable)
        if supplied.is_absolute() or PureWindowsPath(value).anchor or any(part in {"..", ".", ""} for part in portable.split("/")):
            raise WorkspaceError("Use a workspace-relative path without parent traversal")
        parts = supplied.parts
        if any(part.lower() in _PRIVATE_PARTS or part.lower() in _PRIVATE_NAMES
               or part.lower().startswith(".env") or part.lower().endswith((".pem", ".key", ".p12", ".pfx"))
               or re.search(r"(?:^|[._-])(?:secrets?|credentials?|tokens?|cookies?|api[_-]?keys?)(?:[._-]|$)", part, re.I)
               or part.rstrip(" .") != part for part in parts):
            raise WorkspaceError("Credential, configuration and private paths are unavailable")
        current = self.root
        try:
            if _link_like(current):
                raise WorkspaceError("Workspace cannot be replaced with a link")
            for part in parts:
                current = current / part
                try:
                    if _link_like(current):
                        raise WorkspaceError("Symlinks and reparse points are unavailable")
                except FileNotFoundError:
                    pass
            resolved = current.resolve(strict=False)
            if not resolved.is_relative_to(self.root):
                raise WorkspaceError("Path leaves the configured workspace")
            if file and (not current.is_file() or current.suffix.lower() != ".json"):
                raise WorkspaceError("Input must be an existing regular .json file")
            if new_directory and current.exists():
                raise WorkspaceError("Export requires a new directory; existing data is never overwritten")
        except OSError:
            raise WorkspaceError("Could not inspect the workspace path") from None
        return current

    def read(self, value):
        path = self.path(value, file=True)
        try:
            before = path.stat()
            if before.st_size > self.max_file_bytes:
                raise WorkspaceError("JSON exceeds configured max_file_bytes")
            if before.st_nlink != 1:
                raise WorkspaceError("Hard-linked files are unavailable")
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, "rb") as stream:
                opened = os.fstat(stream.fileno())
                checked = self.path(value, file=True).stat()
                if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                        or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                        or (opened.st_dev, opened.st_ino) != (checked.st_dev, checked.st_ino)):
                    raise WorkspaceError("Input changed while opening; retry with a stable regular file")
                data = stream.read(self.max_file_bytes + 1)
            if len(data) > self.max_file_bytes:
                raise WorkspaceError("JSON exceeds configured max_file_bytes")
            value = strict_json(data.decode("utf-8-sig"))
        except WorkspaceError:
            raise
        except (OSError, UnicodeError, ValueError):
            raise WorkspaceError("Expected stable UTF-8 JSON without duplicate keys, nonfinite numbers or invalid structure") from None
        _public_payload(value)
        return value, hashlib.sha256(data).hexdigest()

    def verdict(self, value):
        """Keep full finding counts and useful paths without flooding a host."""
        value = deepcopy(value)
        findings = value.get("findings", [])
        value["finding_count"] = len(findings)
        value["findings_truncated"] = len(findings) > self.max_findings
        value["findings"] = findings[:self.max_findings]
        value["finding_fields_truncated"] = False
        for finding in value["findings"]:
            field_truncation = {}
            for key in ("message", "path", "code"):
                if isinstance(finding.get(key), str):
                    finding[key], details = _bounded_text(finding[key], self.max_finding_chars)
                    if details is not None:
                        field_truncation[key] = details
            if field_truncation:
                finding["field_truncation"] = field_truncation
                value["finding_fields_truncated"] = True
            for key in ("expected", "actual"):
                if key in finding:
                    encoded = canonical(finding[key])
                    if len(encoded) > 2048:
                        finding[key] = {"preview": encoded[:2000], "truncated": True,
                                        "sha256": digest(finding[key]), "characters": len(encoded)}
                        value["finding_fields_truncated"] = True
        return value

    def selected(self, path, request_id):
        recording, checksum = self.read(path)
        try:
            selected = select_recording(validate_recording(recording), request_id)
        except (TypeError, ValueError, KeyError) as exc:
            raise WorkspaceError("Invalid or ambiguous recording: " + str(exc)) from None
        return selected, checksum

    def inspect_boundary(self, input_path, output_path):
        original, original_sha = self.read(input_path)
        candidate, candidate_sha = self.read(output_path)
        if not isinstance(original, list) or not isinstance(candidate, list):
            raise WorkspaceError("Boundary inputs must be message-array JSON files")
        valid, verdict = compare_messages(original, original), compare_messages(original, candidate)
        return {**self.verdict(valid if valid["status"] != "PASS" else verdict),
                "input_contract": self.verdict(valid), "input_file_sha256": original_sha,
                "output_file_sha256": candidate_sha, "provider_requests": 0,
                "scope": "Checks supplied message semantics; no SDK or application is executed"}

    def check_recording(self, recording_path, request_id=None):
        selected, checksum = self.selected(recording_path, request_id)
        valid = compare_messages(selected["original_input"], selected["original_input"])
        verdict = compare_messages(selected["original_input"], selected["candidate"])
        if selected["payload_redacted"]:
            verdict = {"status": "INCONCLUSIVE", "findings": [{"code": "REDACTED_CAPTURE", "path": "", "message": "Redacted payloads cannot establish preservation of the original input"}]}
        return {**self.verdict(valid if valid["status"] != "PASS" else verdict),
                "input_contract": self.verdict(valid), "recording_file_sha256": checksum,
                "recording": {key: selected[key] for key in ("adapter", "version", "request_id", "payload_redacted")},
                "provider_requests": 0, "scope": "A selected user-supplied capture; producer provenance is not independently authenticated"}

    def compare_recordings(self, baseline_path, candidate_path, baseline_request_id=None, candidate_request_id=None):
        baseline, baseline_sha = self.selected(baseline_path, baseline_request_id)
        candidate, candidate_sha = self.selected(candidate_path, candidate_request_id)
        if baseline["adapter"] != candidate["adapter"]:
            raise WorkspaceError("Recording adapter identities differ")
        if compare_messages(baseline["original_input"], candidate["original_input"])["status"] != "PASS":
            raise WorkspaceError("Recordings must preserve the same valid original input contract")
        contracts = {"baseline": compare_messages(baseline["original_input"], baseline["candidate"]),
                     "candidate": compare_messages(baseline["original_input"], candidate["candidate"]),
                     "difference": compare_messages(baseline["candidate"], candidate["candidate"])}
        verdict = contracts["candidate"]
        direction = "candidate_preserves_contract" if verdict["status"] == "PASS" else "candidate_breaks_or_does_not_establish_contract"
        if contracts["baseline"]["status"] != "PASS":
            verdict = {"status": "NEEDS_REVIEW", "findings": [{"code": "UNHEALTHY_BASELINE", "path": "", "message": "The baseline already fails its original input contract; equal outputs cannot establish compatibility"}]}
            direction = "candidate_restores_contract" if contracts["candidate"]["status"] == "PASS" else "candidate_uncertain"
        if baseline["payload_redacted"] or candidate["payload_redacted"]:
            verdict = {"status": "INCONCLUSIVE", "findings": [{"code": "REDACTED_CAPTURE", "path": "", "message": "Redacted captures cannot establish original message preservation"}]}
            direction = "redacted_capture"
        return {**self.verdict(verdict), "direction": direction,
                "contracts": {key: self.verdict(value) for key, value in contracts.items()},
                "baseline": {"version": baseline["version"], "request_id": baseline["request_id"], "file_sha256": baseline_sha},
                "candidate": {"version": candidate["version"], "request_id": candidate["request_id"], "file_sha256": candidate_sha},
                "adapter": baseline["adapter"], "provider_requests": 0,
                "scope": "Comparison of recorded evidence, with both outputs checked against the same original input; no SDK is executed"}

    def export_regression_gate(self, recording_path, output_dir, request_id=None):
        from .recording_export import _export_gate
        selected, checksum = self.selected(recording_path, request_id)
        if selected["payload_redacted"] or compare_messages(selected["original_input"], selected["original_input"])["status"] != "PASS":
            raise WorkspaceError("Gate export requires a valid supported unredacted original input contract")
        output = self.path(output_dir, new_directory=True)
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output = self.path(output_dir, new_directory=True)
            output.mkdir(exist_ok=False)
            def write(path, value):
                _public_payload(value)
                path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
                return value
            verdict = compare_messages(selected["original_input"], selected["candidate"])
            gate = _export_gate(output, selected, verdict["status"], write=write)
        except WorkspaceError:
            raise
        except (OSError, ValueError):
            raise WorkspaceError("Could not export the gate; prior output is preserved, choose a new directory") from None
        return {"status": "EXPORTED", "observed_status": verdict["status"], "output_dir": output.relative_to(self.root).as_posix(),
                "recording_file_sha256": checksum, "regression_gate": gate, "provider_requests": 0,
                "run_argv": ["python", "-m", "unittest", "discover", "-s", output_dir, "-p", "test_boundary_contract.py"],
                "run_from": "configured workspace",
                "scope": "Standard-library gate for a frozen captured input. A broken observed candidate intentionally fails; this tool does not run the test or a future SDK"}


def create_server(workspace, *, max_file_bytes=8_000_000, max_findings=100, max_finding_chars=2048):
    if sys.version_info < (3, 11):
        raise WorkspaceError("MCP requires Python 3.11+; the base ReviKnot CLI still supports Python 3.10")
    policy = Workspace(workspace, max_file_bytes=max_file_bytes, max_findings=max_findings,
                       max_finding_chars=max_finding_chars)
    try:
        from mcp.server import MCPServer
        from mcp.server.mcpserver.exceptions import ToolError
        from mcp.types import ToolAnnotations
    except ImportError:
        raise WorkspaceError('Install the optional official SDK from this checkout: python -m pip install -e ".[mcp]"; '
                             'for an existing local installation: python -m pip install "mcp>=2,<3" (Python 3.11+)') from None
    from . import __version__
    server = MCPServer("ReviKnot", version=__version__, log_level="WARNING", instructions=
        "Verify captured agent message boundaries before approving SDK changes. Tools read only explicit relative JSON files inside the configured workspace. "
        "Check the original input contract: identical broken outputs are not compatible. Use finding paths to repair your adapter, capture it again, then compare and export a gate. "
        "No model, network, shell, package installation or application execution is performed by these tools. The host decides whether and when to call them.")
    read_only = ToolAnnotations(read_only_hint=True, open_world_hint=False)
    def run(function, *args):
        try:
            return function(*args)
        except WorkspaceError as exc:
            raise ToolError(bounded_error(str(exc), policy.max_finding_chars)) from None
    @server.tool(annotations=read_only, structured_output=True)
    def inspect_boundary(input_path: str, output_path: str) -> dict[str, object]:
        """Check a captured output against its original message-array JSON input; returns semantic finding paths. Both file paths are relative to the configured workspace."""
        return run(policy.inspect_boundary, input_path, output_path)
    @server.tool(annotations=read_only, structured_output=True)
    def check_recording(recording_path: str, request_id: str | None = None) -> dict[str, object]:
        """Check one BoundaryRecorder transaction without writing files. Select request_id when a recording contains multiple transactions."""
        return run(policy.check_recording, recording_path, request_id)
    @server.tool(annotations=read_only, structured_output=True)
    def compare_recordings(baseline_path: str, candidate_path: str, baseline_request_id: str | None = None, candidate_request_id: str | None = None) -> dict[str, object]:
        """Compare two recorded versions of the same adapter and original input. An unhealthy baseline remains NEEDS_REVIEW even if the candidate restores the contract."""
        return run(policy.compare_recordings, baseline_path, candidate_path, baseline_request_id, candidate_request_id)
    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False), structured_output=True)
    def export_regression_gate(recording_path: str, output_dir: str, request_id: str | None = None) -> dict[str, object]:
        """Write a portable Python standard-library regression gate into a NEW workspace-relative directory. Never overwrites existing data or runs code. Broken observations intentionally produce a failing default test."""
        return run(policy.export_regression_gate, recording_path, output_dir, request_id)
    return server


def serve(workspace, *, max_file_bytes=8_000_000, max_findings=100, max_finding_chars=2048):
    server = create_server(workspace, max_file_bytes=max_file_bytes, max_findings=max_findings,
                           max_finding_chars=max_finding_chars)
    server.run(transport="stdio")
    return 0
