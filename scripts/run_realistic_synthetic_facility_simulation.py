from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.simulations.realistic_synthetic_facilities import (  # noqa: E402
    load_synthetic_dataset,
    run_synthetic_decision_simulation,
)


JSON_PATH = REPO_ROOT / "reports" / "REALISTIC_SYNTHETIC_FACILITY_SIMULATION.json"
MD_PATH = REPO_ROOT / "reports" / "REALISTIC_SYNTHETIC_FACILITY_SIMULATION.md"


def _markdown(report: dict) -> str:
    lines = [
        "# Realistic Synthetic Facility Simulation",
        "",
        f"- Dataset: `{report['dataset_id']}`",
        "- Boundary: synthetic validation data only; canonical facility data is unchanged.",
        f"- Result: **{'PASS' if report['pass'] else 'FAIL'}**",
        "",
        "## Coverage Distribution",
        "",
        "| Facility | Known coverage | Unknown | Missing | Stale | Contradicted | N/A |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["validation"]["facility_coverage"]:
        lines.append(
            f"| {row['facility_name']} | {row['coverage_pct']}% | {row['unknown_count']} | "
            f"{row['missing_count']} | {row['stale_count']} | {row['contradiction_count']} | {row['not_applicable_count']} |"
        )

    lines.extend(["", "## Ranking Outcome", "", "| Rank | Facility | Archetype | Eligibility | Match | Evidence certainty | Quality |", "| --- | --- | --- | --- | ---: | ---: | ---: |"])
    for row in report["ranking"]:
        lines.append(
            f"| {row['rank']} | {row['facility_name']} | {row['archetype']} | {row['eligibility']} | "
            f"{row['match_score']} | {row['evidence_certainty']} | {row['quality_safety_score']} |"
        )

    lines.extend(["", "## Behavioral Assertions", ""])
    for name, passed in report["assertions"].items():
        lines.append(f"- {name.replace('_', ' ').title()}: **{'PASS' if passed else 'FAIL'}**")

    lines.extend(["", "## Contradiction And Missingness Trace", ""])
    for row in report["ranking"]:
        special = row["evidence_state_notes"]
        if not special:
            continue
        lines.append(f"### {row['facility_name']}")
        lines.append("")
        for note in special:
            lines.append(f"- `{note['parameter_id']}`: **{note['evidence_state']}** — {note['reason']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    report = run_synthetic_decision_simulation(load_synthetic_dataset())
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    JSON_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    MD_PATH.write_text(_markdown(report), encoding="utf-8")
    print(f"WROTE {JSON_PATH}")
    print(f"WROTE {MD_PATH}")
    print(f"REALISTIC_SYNTHETIC_SIMULATION={'PASS' if report['pass'] else 'FAIL'}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())