"""Copy tracked and nonignored source to a new directory outside this checkout."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
out = args.output.resolve()
if out == root or root in out.parents or out.exists():
    parser.error("Choose a new output directory outside the repository")
files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
manifest = {}
for name in sorted(set(filter(None, files))):
    source = root / name
    if not source.is_file():
        continue
    parts = Path(name).parts
    if source.is_symlink() or any(p.startswith('.env') and p != '.env.example' for p in parts) or source.suffix in {'.db','.sqlite','.sqlite3','.pem','.key'}:
        raise SystemExit(f"Excluded file unexpectedly eligible for release: {name}")
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    manifest[name] = hashlib.sha256(source.read_bytes()).hexdigest()
(out / "SOURCE_MANIFEST.json").write_text(json.dumps({"files": [{"path": name, "sha256": digest} for name, digest in manifest.items()]}, indent=2) + "\n")
print(json.dumps({"source_files": len(manifest), "output": str(out), "private_environment_included": False}))
