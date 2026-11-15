"""Run family personas against the 450 synthetic Israeli facilities.

For each persona: how many facilities pass every MUST, how many are pending
(the facility has not answered something the family needs), how many fail and why,
and the top of the ranking with the preferences each one matched or missed.

Runs fully offline: the synthetic registrations are applied in memory exactly as
the live engine applies stored registrations. Distance is not used yet (facility
addresses are not geocoded in the engine), so city appears only in the report.

Usage: python scripts/run_israel_synthetic_scenarios.py [--out reports/israel_synthetic_runs.md]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["OPTIME_CANONICAL_MARKET"] = "israel-synthetic"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/oomnik_il_synthetic_runs.db")

from app.database import Base, engine  # noqa: E402
import app.models.facility  # noqa: E402,F401
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent, intent_rank_key  # noqa: E402
from app.services.israel_facility_registration import apply_registration  # noqa: E402

DATA = ROOT / "database" / "israel_synthetic"

PERSONAS = [
    ("אמא סיעודית, קוד משרד הבריאות, דוברת רוסית, מסורתית", {
        "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "חיפה", "residentGenders": ["FEMALE"],
        "language": "RU", "community": "TRADITIONAL", "kashrut": "KOSHER"}),
    ("אבא תשוש נפש שנוטה לשוטט, פרטי עד ₪16,000, חרדי", {
        "functionalLevel": "COGNITIVE_FRAIL", "fundingPathway": "PRIVATE", "monthlyBudgetIls": 16000, "city": "ירושלים",
        "residentGenders": ["MALE"], "medicalNeeds": ["WANDERING"], "community": "HAREDI", "kashrut": "MEHADRIN", "shabbat": "IMPORTANT"}),
    ("זוג: היא עצמאית, הוא סיעודי, פרטי עד ₪20,000", {
        "functionalLevel": "NURSING", "fundingPathway": "PRIVATE", "monthlyBudgetIls": 20000, "city": "רעננה",
        "isCouple": True, "partnerSameLevel": False, "residentGenders": ["FEMALE", "MALE"]}),
    ("מונשם, קוד משרד הבריאות", {
        "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "תל אביב - יפו", "residentGenders": ["MALE"],
        "medicalNeeds": ["VENTILATION"]}),
    ("אישה עצמאית, דיור מוגן פרטי, חילונית, ממ\"ד חשוב", {
        "functionalLevel": "INDEPENDENT", "fundingPathway": "PRIVATE", "monthlyBudgetIls": 9000, "city": "הרצליה",
        "residentGenders": ["FEMALE"], "community": "SECULAR", "shelterInRoom": "IMPORTANT"}),
    ("אבא דרוזי סיעודי עם PEG, קוד", {
        "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "דלית אל-כרמל", "residentGenders": ["MALE"],
        "medicalNeeds": ["PEG"], "language": "AR", "community": "DRUZE"}),
    ("אמא מוסלמית תשושה, סיוע רווחה, ערבית", {
        "functionalLevel": "FRAIL", "fundingPathway": "WELFARE_ASSISTANCE", "city": "נצרת", "residentGenders": ["FEMALE"],
        "language": "AR", "community": "MUSLIM"}),
    ("מצב תפקודי לא ברור", {"functionalLevel": "UNCLEAR", "fundingPathway": "UNCLEAR", "city": "באר שבע"}),
]

GATE_HE = {
    "IL_FUNCTIONAL_LEVEL": "רמת תפקוד",
    "IL_MOH_CODE_AGREEMENT": "הסכם קוד",
    "IL_ACCEPTS_VENTILATED": "מונשמים",
    "IL_WANDERING_SAFE": "משוטטים",
    "IL_ACCEPTS_PEG": "PEG",
    "IL_ACCEPTS_NG_TUBE": "זונדה",
    "IL_ACCEPTS_COUPLE": "זוגות",
    "IL_GENDER_POLICY": "מגדר",
    "IL_FUNDING_TRACK": "מסלול מימון",
    "LICENSE_CURRENTLY_VALID": "רישיון בתוקף",
    "IL_COMMUNITY": "ציבור",
    "IL_KASHRUT": "כשרות",
    "IL_SHABBAT": "שבת",
    "IL_LANGUAGE": "שפה",
    "IL_SHELTER": "ממ\"ד",
    "IL_BUDGET": "תקציב",
    "IL_AVAILABILITY": "זמינות",
}


def he(keys) -> str:
    return ", ".join(GATE_HE.get(k, k) for k in keys) or "-"


def load_rows():
    records = json.loads((DATA / "facility_universe.json").read_text(encoding="utf-8"))["records"]
    registrations = json.loads((DATA / "registrations.json").read_text(encoding="utf-8"))["registrations"]
    return [apply_registration(r, registrations.get(r["canonical_id"])) for r in records]


def run(rows, family):
    intent = build_client_intent({"israelMarket": family}, "", {}, {})
    results = []
    for row in rows:
        fit = evaluate_candidate_intent(row, intent)
        results.append((row, fit))
    gates = Counter(fit["hard_gate"] for _, fit in results)
    fail_reasons = Counter(k for _, fit in results for k in fit["must_fail"])
    pending_reasons = Counter(k for _, fit in results if fit["hard_gate"] != "FAIL" for k in fit["must_unknown"])
    passing = sorted(
        (item for item in results if item[1]["hard_gate"] == "PASS"),
        key=lambda item: intent_rank_key({"client_intent_fit": item[1]}),
    )
    return intent, gates, fail_reasons, pending_reasons, passing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "reports" / "israel_synthetic_runs.md"))
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    rows = load_rows()

    lines = [
        "# הרצות על 450 מוסדות סינתטיים",
        "",
        "נתונים סינתטיים בלבד. המרחק עוד לא משפיע על הדירוג (אין גיאוקוד בכתובות המוסדות במנוע).",
        "",
    ]
    for title, family in PERSONAS:
        intent, gates, fails, pendings, passing = run(rows, family)
        lines += [
            f"## {title}",
            "",
            f"- תנאי חובה: {he(m['key'] for m in intent['must_haves'])}",
            f"- העדפות: {he(n['key'] for n in intent['nice_to_haves'] if n['key'].startswith('IL_'))}",
            f"- עוברים את כל החובה: **{gates.get('PASS', 0)}** · ממתינים למידע: **{gates.get('PENDING_VERIFICATION', 0)}** · נפסלים: **{gates.get('FAIL', 0)}**",
            f"- סיבות פסילה: {', '.join(f'{GATE_HE.get(k, k)} ({n})' for k, n in fails.most_common()) or '-'}",
            f"- חסר מידע מהמוסד על: {', '.join(f'{GATE_HE.get(k, k)} ({n})' for k, n in pendings.most_common()) or '-'}",
            "",
            "| # | מוסד | עיר | התאים | לא התאים |",
            "|---|---|---|---|---|",
        ]
        for rank, (row, fit) in enumerate(passing[:5], 1):
            lines.append(f"| {rank} | {row['facility_name']} | {row['city']} | {he(fit['nice_match'])} | {he(fit['nice_mismatch'])} |")
        if not passing:
            lines.append("| - | אין מוסד שעובר את כל תנאי החובה | | | |")
        lines.append("")
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
