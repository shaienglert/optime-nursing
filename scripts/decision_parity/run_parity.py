"""Decision-engine behaviour parity: run fixed cases against two backends and diff.

Usage:
    python scripts/decision_parity/run_parity.py snapshot <backend_dir> <out_dir>
    python scripts/decision_parity/run_parity.py compare <baseline_dir> <candidate_dir>
    python scripts/decision_parity/run_parity.py check <baseline_backend> <candidate_backend>

Each case runs in its own interpreter (fresh imports, fresh SQLite database) and records
everything the engine exposes: library calls, the three decision HTTP endpoints, and
every database row the case writes. Volatile values (timings, ids, timestamps) are
normalized; the interview AI is fixed; background daemon threads are not started, so a
run is reproducible. A structural refactor must produce zero differences. A change
that is meant to alter decisions will show exactly which outputs moved.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cases import CASES  # noqa: E402
from diff_snaps import walk  # noqa: E402


def _warm_cache(backend: Path) -> None:
    """Materialize the market projection once before running cases in parallel."""
    code = (
        "import os; os.environ.setdefault('OPTIME_CANONICAL_MARKET','las-vegas');"
        "from app.services.canonical_universe import resolve_canonical_universe_path as r; r('las-vegas')"
    )
    subprocess.run([sys.executable, "-c", code], cwd=backend, check=True, env=_env(backend))


def _env(backend: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONPATH"] = str(backend)
    env.pop("OPTIME_SEMANTIC_AI_API_KEY", None)
    return env


def snapshot(backend: str, out: str, workers: int = 4) -> int:
    backend_dir, out_dir = Path(backend).resolve(), Path(out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    _warm_cache(backend_dir)

    def run(case: str) -> tuple[str, int]:
        with open(out_dir / f"{case}.log", "w") as log:
            proc = subprocess.run(
                [sys.executable, str(HERE / "parity_case.py"), str(backend_dir), case, str(out_dir / f"{case}.json")],
                cwd=backend_dir, env=_env(backend_dir), stdout=log, stderr=subprocess.STDOUT, timeout=900,
            )
        return case, proc.returncode

    failed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for case, code in pool.map(run, CASES):
            print(f"{case}: {'ok' if code == 0 else f'FAILED (exit {code}, see {out_dir / (case + '.log')})'}")
            failed += code != 0
    return 1 if failed else 0


def compare(baseline: str, candidate: str, show: int = 12) -> int:
    base_dir, cand_dir = Path(baseline), Path(candidate)
    total = 0
    allowed = 0
    for case in CASES:
        a, b = base_dir / f"{case}.json", cand_dir / f"{case}.json"
        if not a.exists() or not b.exists():
            print(f"{case}: MISSING snapshot")
            total += 1
            continue
        diffs: list = []
        walk(json.loads(a.read_text()), json.loads(b.read_text()), "$", diffs)
        total += len(diffs)
        # Owner-approved additive contract fields from the authority integration.
        # Changed values and removals still fail; only absent -> present is exempt.
        allowed += sum(
            kind == "added" and (
                path == "$.http_recommendations.body.decision_id"
                # Additive intake-reuse contract. Existing signals, decisions,
                # ordering and database writes must still match exactly.
                or path in {
                    "$.http_profile.body.intake_profile_id",
                    "$.profile.care_delivery_signals",
                    "$.run_limit5.patient_needs_profile.care_delivery_signals",
                    "$.run_limit50.patient_needs_profile.care_delivery_signals",
                    "$.http_recommendations.body.patient_needs_profile.care_delivery_signals",
                }
                or path.endswith(".intake_resolution")
                or path.endswith(".source_backed_conflict_keys")
            )
            for path, kind, _old, _new in diffs
        )
        print(f"{case}: {'identical' if not diffs else f'{len(diffs)} differences'}")
        for path, kind, x, y in diffs[:show]:
            print(f"    {path} [{kind}] {json.dumps(x, default=str)[:100]} -> {json.dumps(y, default=str)[:100]}")
    print(f"TOTAL_DIFFERENCES={total}")
    print(f"ALLOWED_ADDITIONS={allowed}")
    print(f"UNEXPECTED_DIFFERENCES={total - allowed}")
    return 1 if total > allowed else 0


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "snapshot":
        return snapshot(argv[1], argv[2])
    if len(argv) == 3 and argv[0] == "compare":
        return compare(argv[1], argv[2])
    if len(argv) == 3 and argv[0] == "check":
        root = Path(os.environ.get("PARITY_OUT", "parity-out"))
        if snapshot(argv[1], str(root / "baseline")) or snapshot(argv[2], str(root / "candidate")):
            return 2
        return compare(str(root / "baseline"), str(root / "candidate"))
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
