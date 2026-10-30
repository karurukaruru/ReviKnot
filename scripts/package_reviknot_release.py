"""Package the current ReviKnot worktree and verified local judge replay.

No commit, upload, installation, model call or Git-history export is performed.
The current worktree, including new untracked source/tests, is authoritative.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from patchcourt import __version__
from scripts.package_judge_demo import package as package_judge


VERSION_TAG = __version__.replace(".", "")
RELEASE_REVIEW = f"RELEASE_REVIEW_{VERSION_TAG}_ZH.md"
SUBMISSION_DOCS = f"docs/submission-{VERSION_TAG}"
EXCLUDED_PARTS = {".git", ".venv", ".venv-dev", "venv", "node_modules", "__pycache__",
                  ".pytest_cache", ".sdk-environments", ".sdk-nvidia", ".sdk-crewai",
                  ".video-deps", ".test-deps", ".wheelhouse", ".local-tmp", "build", "dist",
                  "outputs", "release", "private"}
MATERIALS = ("DEVPOST_SUBMISSION.md", "MOST_VALUABLE_FEEDBACK.md", "DEMO_SCRIPT.md",
             "JUDGE_TESTING.md", "SUBMISSION_CHECKLIST.md", "OUTPUT_SETTINGS_ZH.md",
             RELEASE_REVIEW, "MCP.md", "MCP.zh-CN.md", "QUICKSTART.md",
             "SOURCE_REVIEW.md", "TESTING.md")
SENSITIVE_NAMES = {"config.json", "credentials.json", "cookies.json", "token.json",
                   "新建 文本文档.txt"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def excluded(name):
    path = PurePosixPath(name)
    return (path.is_absolute() or ".." in path.parts
            or any(part in EXCLUDED_PARTS or part.startswith(".venv-")
                   or part.endswith(".egg-info") for part in path.parts)
            or path.name in SENSITIVE_NAMES
            or (path.name.startswith(".env") and path.name != ".env.example")
            or path.suffix.lower() in {".pyc", ".pyo", ".crdownload", ".lock"})


def credential_values(credential_file):
    values = {value.encode() for key, value in os.environ.items()
              if any(marker in key.upper() for marker in ("API_KEY", "ACCESS_TOKEN", "SECRET", "PASSWORD"))
              and len(value) >= 12}
    if credential_file:
        for line in credential_file.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
            if not match:
                continue
            key, value = match.groups()
            if not any(marker in key.upper() for marker in ("API_KEY", "ACCESS_TOKEN", "SECRET", "PASSWORD")):
                continue
            value = value.strip().strip("\"'")
            if len(value) >= 12:
                values.add(value.encode())
    return values


def scan(data, name, values, depth=0):
    if any(value in data for value in values):
        raise ValueError("Known credential found in " + name + "; value suppressed")
    if re.search(rb"\b(?:sk-proj-|tvly-)[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data):
        raise ValueError("Credential-shaped content found in " + name + "; value suppressed")
    if name.lower().endswith((".zip", ".whl")):
        if depth >= 3:
            raise ValueError("Nested archive scan depth exceeded: " + name)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 200_000_000:
                raise ValueError("Nested archive scan size exceeded: " + name)
            for info in archive.infolist():
                if not info.is_dir():
                    scan(archive.read(info), name + "!" + info.filename, values, depth + 1)


def source_files(values):
    listed = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    records = {}
    for name in listed.decode("utf-8").split("\0"):
        if not name or excluded(name):
            continue
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError("Unsafe source path: " + name)
        if not path.exists():
            continue  # A deletion in the current worktree is a deletion in the release.
        if not path.is_file():
            raise ValueError("Source input must be a regular file: " + name)
        data = path.read_bytes()
        scan(data, name, values)
        records[name] = data
    required = {"pyproject.toml", "reviknot/__init__.py", "reviknot/__main__.py", "reviknot/cli.py",
                "README.md", "LICENSE", "tests/test_submission_model_json.py", "patchcourt/mcp_server.py",
                "tests/test_reviknot_mcp_workspace.py", "tests/test_reviknot_mcp_stdio.py",
                "scripts/mcp_evidence.py", "scripts/verify_mcp_workflow.py", "examples/refund-agent/capture.py"}
    if not required.issubset(records):
        raise ValueError("Current source package is incomplete")
    return records


def write_zip(path, entries, metadata):
    if path.exists():
        raise ValueError("Preserve existing archive; choose a new output directory")
    manifest = dict(metadata, files={name: {"sha256": digest(data), "bytes": len(data)}
                                    for name, data in sorted(entries.items())})
    manifest_name = "RELEASE-MANIFEST.json"
    if manifest_name in entries:
        raise ValueError("Reserved manifest path already exists")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)
        archive.writestr(manifest_name, json.dumps(manifest, ensure_ascii=False, indent=2).encode())
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Archive CRC or unique member validation failed")
        if set(archive.namelist()) != set(entries) | {manifest_name}:
            raise ValueError("Archive member list differs")
        for name, data in entries.items():
            if digest(archive.read(name)) != digest(data):
                raise ValueError("Archive member verification failed: " + name)
        if json.loads(archive.read(manifest_name)) != manifest:
            raise ValueError("Archive manifest verification failed")
    checksum = digest(path.read_bytes())
    path.with_name(path.name + ".sha256").write_text(checksum + "  " + path.name + "\n", encoding="ascii")
    return {"file": str(path), "sha256": checksum, "bytes": path.stat().st_size,
            "members": len(entries) + 1, "all_member_hashes_verified": True, "crc_verified": True}


def verify_judge_package(result):
    folder, archive_path = Path(result["directory"]), Path(result["archive"])
    files = {path.relative_to(folder).as_posix(): path.read_bytes()
             for path in folder.rglob("*") if path.is_file()}
    manifest = json.loads(files["package-manifest.json"])
    expected = {name: digest(data) for name, data in files.items() if name != "package-manifest.json"}
    if manifest["files"] != expected:
        raise ValueError("Judge directory manifest differs from exported files")
    with zipfile.ZipFile(archive_path) as archive:
        if (archive.testzip() is not None or len(archive.namelist()) != len(set(archive.namelist()))
                or set(archive.namelist()) != set(files)):
            raise ValueError("Judge archive CRC or member list differs")
        if any(digest(archive.read(name)) != digest(data) for name, data in files.items()):
            raise ValueError("Judge archive member hash differs")
    if digest(archive_path.read_bytes()) != result["sha256"]:
        raise ValueError("Judge archive checksum differs")
    result.update(all_member_hashes_verified=True, crc_verified=True, members=len(files))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-report", type=Path, required=True, help="Verified live-run directory")
    parser.add_argument("--sdk-report", type=Path, required=True, help="Recorded installed-SDK upgrade directory")
    parser.add_argument("--gate-dir", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--mcp-evidence", type=Path, help="Verified official-client MCP workflow directory to include in the judge portal")
    parser.add_argument("--credential-file", type=Path, help="Local env file used only for secret-value scanning")
    parser.add_argument("--dry-run", action="store_true", help="Scan current source without writing a package")
    args = parser.parse_args()
    values = credential_values(args.credential_file)
    entries = source_files(values)
    for name in MATERIALS:
        if name not in entries:
            raise ValueError("Current submission material is missing: " + name)
    submission_docs = {name: data for name, data in entries.items() if name.startswith(SUBMISSION_DOCS + "/")}
    if not submission_docs:
        raise ValueError("Current bilingual submission documents are missing")
    wheel_data = args.wheel.read_bytes()
    scan(wheel_data, args.wheel.name, values)
    if args.mcp_evidence is not None:
        from scripts.mcp_evidence import verify_mcp_evidence
        verify_mcp_evidence(args.mcp_evidence)
    if args.dry_run:
        print(json.dumps({"status": "SCANNED", "source_files": len(entries),
                          "source_bytes": sum(map(len, entries.values())), "secrets_included": False}))
        return
    output = args.output.resolve()
    if output == ROOT or output.is_relative_to(ROOT):
        raise ValueError("Delivery directory must be outside the source worktree")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Delivery directory must be new or empty; existing deliveries are preserved")
    output.mkdir(parents=True, exist_ok=True)
    folders = {"source": output / "01_源码_Source", "wheel": output / "02_运行包_Python",
               "judge": output / "03_评委演示_Judge-Demo", "copy": output / "04_提交文案_Submission-Copy",
               "qa": output / "05_验收_Evidence"}
    for folder in folders.values():
        folder.mkdir()
    judge = package_judge(args.live_report, args.sdk_report, folders["judge"] / f"ReviKnot-Judge-Demo-{__version__}",
                          wheel=args.wheel, gate_dir=args.gate_dir, mcp_evidence=args.mcp_evidence)
    verify_judge_package(judge)
    # The judge package revalidates live evidence, actual SDK evidence, wheel and gate.
    for path in folders["judge"].rglob("*"):
        if path.is_file():
            scan(path.read_bytes(), path.relative_to(output).as_posix(), values)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    metadata = {"version": __version__, "product": "ReviKnot", "source": "current local worktree",
                "git_baseline_head": head, "baseline_head_is_release_commit": False,
                "contains_uncommitted_source": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip()),
                "secrets_included": False, "packaging_network_calls": 0,
                "note": "Hashes establish local artifact integrity, not provider authenticity or competition submission."}
    source = write_zip(folders["source"] / f"ReviKnot-{__version__}-Source.zip", entries, metadata)
    shutil.copyfile(args.wheel, folders["wheel"] / args.wheel.name)
    for name in MATERIALS:
        (folders["copy"] / name).write_bytes(entries[name])
    for name, data in submission_docs.items():
        relative = PurePosixPath(name).relative_to(SUBMISSION_DOCS)
        target = folders["copy"] / Path(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result = {"status": "PASS", **metadata, "source": source, "judge": judge,
              "wheel": {"name": args.wheel.name, "sha256": digest(wheel_data)},
              "known_credential_scan": "PASS", "source_files": len(entries)}
    (folders["qa"] / "PACKAGE_VERIFICATION.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "先看这里_START-HERE.txt").write_text(
        f"ReviKnot {__version__} 本地参赛交付 / Local submission delivery\n\n"
        f"01 源码：解压 Source.zip 后先读 README.zh-CN.md 和 {RELEASE_REVIEW}。\n"
        f"02 Python 运行包：pip install reviknot-{__version__}-py3-none-any.whl；python -m reviknot demo。\n"
        "03 评委演示：解压 Judge-Demo.zip，Windows 双击 Start-Judge-Demo.cmd。历史实测回放不调用 API。\n"
        "04 提交文案：先看 00_START_HERE_先看这里.md 和 SUBMISSION_CHECKLIST.md，再复制英文表单文案。\n"
        "05 验收：包校验结果和每个源码文件的 SHA-256 位于相应 manifest。\n"
        "MCP：Python3.11+可选接入，详见MCP.zh-CN.md（English:MCP.md）；评委页的MCP卡片是已录制的真实stdio客户端验证。\n\n"
        "视频另行交付。本目录未上传 GitHub、YouTube 或比赛网站，也不包含密钥。\n"
        "Recorded playback requires no API key. Source is the current local worktree, including uncommitted files.\n",
        encoding="utf-8")
    files = {path.relative_to(output).as_posix(): digest(path.read_bytes())
             for path in output.rglob("*") if path.is_file()}
    (output / "DELIVERY-MANIFEST.json").write_text(json.dumps({"product": "ReviKnot", "version": __version__,
        "files": files, "self_excluded": True, "published": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
