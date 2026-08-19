from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "app" / "main.py"

text = MAIN.read_text(encoding="utf-8")
original = text

old_import = '''from app.services.patient_decision_engine import (\n    build_patient_comparison_context,\n    build_patient_needs_profile,\n    run_patient_decision_engine,\n)'''
new_import = '''from app.services.patient_decision_engine import (\n    _regulatory_index,\n    build_patient_comparison_context,\n    build_patient_needs_profile,\n    run_patient_decision_engine,\n)'''
if old_import in text:
    text = text.replace(old_import, new_import, 1)
elif new_import not in text:
    raise SystemExit("patient_decision_engine import block did not match expected source")

old_assignment = '''        result["facility_profile_id"] = ccn_to_facility_id.get(cms_ccn)'''
new_assignment = '''        legacy_profile_id = ccn_to_facility_id.get(cms_ccn)\n        result["facility_profile_id"] = (\n            legacy_profile_id\n            if legacy_profile_id is not None\n            else ("canonical" if result.get("canonical_facility_id") else None)\n        )'''
if old_assignment in text:
    text = text.replace(old_assignment, new_assignment, 1)
elif new_assignment not in text:
    raise SystemExit("facility_profile_id assignment did not match expected source")

marker = '''@app.post("/canonical-facilities/parameter-comparison", response_model=FacilityParameterComparisonOut)'''
endpoint = '''@app.get("/canonical-facilities/{canonical_id}/regulatory-history")\nasync def get_canonical_facility_regulatory_history(canonical_id: str):\n    canonical_index = get_canonical_facility_index()\n    facility = canonical_index.get(canonical_id)\n    if not facility:\n        raise HTTPException(status_code=404, detail="Canonical facility not found")\n\n    history = _regulatory_index().get(canonical_id)\n    return {\n        "canonical_facility_id": canonical_id,\n        "facility_name": facility.get("name") or facility.get("facility_name") or facility.get("community_name"),\n        "source": "Nevada HCQC / ALiS" if history else None,\n        "regulatory_history": history,\n    }\n\n\n'''
if endpoint not in text:
    if marker not in text:
        raise SystemExit("canonical comparison endpoint marker not found")
    text = text.replace(marker, endpoint + marker, 1)

if text != original:
    MAIN.write_text(text, encoding="utf-8")
    print("patched backend/app/main.py")
else:
    print("backend/app/main.py already patched")
