"""Run every backend test, deselecting only the entries in backend/tests/known_failures.txt."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
known = [
    line.strip()
    for line in (ROOT / "backend/tests/known_failures.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]
args = [sys.executable, "-m", "pytest", "backend/tests", "-q", "-p", "no:cacheprovider", "-rfE"]
for entry in known:
    args += ["--ignore", entry] if "::" not in entry else ["--deselect", entry]
args += sys.argv[1:]
print(f"Deselecting {len(known)} known failures listed in backend/tests/known_failures.txt")
raise SystemExit(subprocess.call(args, cwd=ROOT))
