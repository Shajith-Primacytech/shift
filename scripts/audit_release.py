"""Redacted full-history + public-source audit. A finding blocks release."""
import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True, help="Prepared public source directory")
parser.add_argument("--gitleaks", default="gitleaks")
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve()
if not (source / "SOURCE_MANIFEST.json").is_file():
    parser.error("Prepare the public source directory first")
# Exact private-value checks complement the scanner's provider/entropy rules.
private = set()
for path in [root / "backend/.env", root / "backend/data/judge-accounts.env"]:
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            name, value = line.split("=", 1)
            if any(word in name.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
                value = value.strip().strip('"\'')
                if len(value) >= 12:
                    private.add(value.encode())
if os.environ.get("AMD_API_KEY"):
    private.add(os.environ["AMD_API_KEY"].encode())
commits = subprocess.check_output(["git", "rev-list", "--all", "--reflog"], cwd=root).decode().splitlines()
exact = []
versions = 0
for commit in commits:
    for entry in subprocess.check_output(["git", "ls-tree", "-rz", commit], cwd=root).split(b"\0"):
        if not entry:
            continue
        meta, name = entry.split(b"\t", 1)
        if meta.split()[1] != b"blob":
            continue
        data = subprocess.check_output(["git", "cat-file", "blob", meta.split()[2].decode()], cwd=root)
        versions += 1
        if any(secret in data for secret in private):
            exact.append({"file": name.decode(), "commit": commit, "kind": "private credential match"})
for path in source.rglob("*"):
    if path.is_file() and any(secret in path.read_bytes() for secret in private):
        exact.append({"file": str(path.relative_to(source)), "commit": "public-source", "kind": "private credential match"})
findings = list(exact)
with tempfile.TemporaryDirectory(prefix="shift-audit-") as temp:
    for name, command in [
        ("history", ["git", "--log-opts=--all --reflog --full-history", str(root)]),
        ("public-source", ["dir", str(source)]),
    ]:
        report = Path(temp) / f"{name}.json"
        result = subprocess.run([args.gitleaks, *command, "--no-banner", "--redact=100", "--report-format=json", f"--report-path={report}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode not in (0, 1):
            raise SystemExit("Secret scanner did not complete. Release remains blocked.")
        for item in json.loads(report.read_text()):
            findings.append({"file": item["File"], "commit": item.get("Commit") or name, "rule": item["RuleID"]})
evidence = {"scanned_at": datetime.now(timezone.utc).isoformat(), "scope": "all fetched refs, reflogs, full history, and prepared public source", "commits": len(commits), "file_versions": versions, "private_values_compared": len(private), "findings": findings, "release_scan_passed": not findings}
args.report.write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
if findings:
    raise SystemExit("STOP: credential findings must be addressed before public release")
