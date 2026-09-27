"""Run every acceptance case against the pilot market and report what held and what did not.

    python scripts/pilot_acceptance/run_all.py [--out DIR] [--workers N] [--case KEY]

Exits non-zero if any case fails, so this can gate a merge.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cases import CASES  # noqa: E402


def run_one(case: str, out_dir: Path) -> tuple[str, int]:
    target = out_dir / f"{case}.json"
    with open(out_dir / f"{case}.log", "w", encoding="utf-8") as log:
        proc = subprocess.run(
            [sys.executable, str(HERE / "run_case.py"), case, str(target)],
            cwd=HERE, stdout=log, stderr=subprocess.STDOUT, timeout=1800,
        )
    return case, proc.returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="pilot-acceptance-out")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--case", action="append", help="run only these cases")
    args = parser.parse_args(argv)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = args.case or list(CASES)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(lambda case: run_one(case, out_dir), selected))

    snapshots = []
    for case in selected:
        path = out_dir / f"{case}.json"
        if not path.exists():
            print(f"{case}: CRASHED before writing a result, see {out_dir / (case + '.log')}")
            snapshots.append(None)
            continue
        snapshots.append(json.loads(path.read_text(encoding="utf-8")))

    live = {snapshot["interview_ai"] for snapshot in snapshots if snapshot}
    print(f"\ninterview AI: {'/'.join(sorted(live)) or 'unknown'}"
          f"   pilot catalog exposed: {next((s['pilot_facility_limit'] for s in snapshots if s), '?')} communities")
    print(f"\n{'case':<34}{'shown':>6}{'elig':>6}{'scored':>7}{'ranks':>7}  {'setting':<34}result")
    print("-" * 108)

    failed = 0
    for case, snapshot in zip(selected, snapshots):
        if snapshot is None:
            failed += 1
            continue
        report = snapshot["grade"]
        settings = sorted({str(row["archetype"]) for row in report["recommendations"]}) or ["-"]
        verdict = "PASS" if report["passed"] else "FAIL"
        failed += not report["passed"]
        print(f"{case:<34}{snapshot['shown'] or 0:>6}{snapshot['must_eligible'] or 0:>6}"
              f"{snapshot['scored'] or 0:>7}{report['distinct_ranks']:>7}  "
              f"{', '.join(settings)[:33]:<34}{verdict}")
        for failure in report["failures"]:
            print(f"    - {failure}")

    total = len([s for s in snapshots if s is not None])
    print(f"\n{total - failed}/{len(selected)} cases pass")
    if "MOCKED" in live:
        print("NOTE: the interview AI was mocked, so ranking quality is not exercised. "
              "Set OPTIME_SEMANTIC_AI_API_KEY to run it for real.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
