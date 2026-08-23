from pathlib import Path
import json

path = Path('backend/app/services/client_intent_runtime.py')
text = path.read_text()

old = '''    city = str(questionnaire_state.get("locationCity") or questionnaire_state.get("city") or "").strip().upper()\n    if "las vegas" in query or city == "LAS VEGAS":\n        add_must("LAS_VEGAS", "The requested market is Las Vegas.", "canonical city/state")\n'''
new = '''    city = str(questionnaire_state.get("locationCity") or questionnaire_state.get("city") or "").strip().upper()\n    las_vegas_requested = "las vegas" in query or city == "LAS VEGAS"\n    city_limits_only = any(token in query for token in ("las vegas city limits", "city limits only", "within las vegas city", "only in las vegas city"))\n    if las_vegas_requested:\n        if city_limits_only:\n            add_must("LAS_VEGAS_CITY_LIMITS", "The client explicitly restricted the search to Las Vegas city limits.", "canonical city/state")\n        else:\n            add_must("LAS_VEGAS", "The requested market is the Las Vegas Valley/metro area unless the client explicitly narrows to city limits.", "canonical Las Vegas Valley market geography")\n'''
if old not in text:
    raise SystemExit('build_client_intent location block not found')
text = text.replace(old, new, 1)

old = '''        if key == "LAS_VEGAS":\n            if state == "NV" and city == "LAS VEGAS":\n                must_pass.append(key)\n            else:\n                hard_fail.append(key)\n        elif key == "NO_FORCED_MEMORY_PLACEMENT":\n'''
new = '''        if key == "LAS_VEGAS":\n            las_vegas_valley_cities = {\n                "LAS VEGAS", "HENDERSON", "NORTH LAS VEGAS", "PARADISE",\n                "SPRING VALLEY", "ENTERPRISE", "WINCHESTER", "SUNRISE MANOR",\n            }\n            if state == "NV" and city in las_vegas_valley_cities:\n                must_pass.append(key)\n            else:\n                hard_fail.append(key)\n        elif key == "LAS_VEGAS_CITY_LIMITS":\n            if state == "NV" and city == "LAS VEGAS":\n                must_pass.append(key)\n            else:\n                hard_fail.append(key)\n        elif key == "NO_FORCED_MEMORY_PLACEMENT":\n'''
if old not in text:
    raise SystemExit('evaluate location block not found')
text = text.replace(old, new, 1)

old = '''    history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}\n    disciplinary = _upper(history.get("disciplinary_action"))\n    disciplinary_order = 0 if disciplinary == "N" else (2 if disciplinary == "Y" else 1)\n    counts = history.get("grade_counts") if isinstance(history.get("grade_counts"), dict) else {}\n    latest_grade = _upper(history.get("latest_known_grade"))\n    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "UNKNOWN": 4}.get(latest_grade, 4)\n\n    reputation = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}\n'''
new = '''    history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}\n\n    reputation = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}\n'''
if old not in text:
    raise SystemExit('regulatory pre-block not found')
text = text.replace(old, new, 1)

old = '''    modalities = {_upper(row.get("canonical_type"))}\n    modalities.update(_upper(value) for value in row.get("housing_modalities") or [])\n    if care_status == "POSSIBLE_FIT" and ("INDEPENDENT_LIVING" in modalities or "LIFE_PLAN_CCRC" in modalities):\n        setting_order = 0\n    else:\n        setting_order = {"PRIMARY_FIT": 0, "POSSIBLE_FIT": 1, "OVERLEVEL": 2, "INSUFFICIENT_SETTING": 3}.get(care_status, 1)\n\n    return (\n'''
new = '''    modalities = {_upper(row.get("canonical_type"))}\n    modalities.update(_upper(value) for value in row.get("housing_modalities") or [])\n    if care_status == "POSSIBLE_FIT" and ("INDEPENDENT_LIVING" in modalities or "LIFE_PLAN_CCRC" in modalities):\n        setting_order = 0\n    else:\n        setting_order = {"PRIMARY_FIT": 0, "POSSIBLE_FIT": 1, "OVERLEVEL": 2, "INSUFFICIENT_SETTING": 3}.get(care_status, 1)\n\n    # Standalone Independent Living is not licensed as an RFG in Nevada. Missing\n    # HCQC RFG grades are NOT_APPLICABLE, not lower-quality evidence. Known\n    # adverse regulatory history still penalizes licensed/hybrid products.\n    pure_independent = (\n        _upper(row.get("canonical_type")) == "INDEPENDENT_LIVING"\n        and "ASSISTED_LIVING" not in modalities\n        and "ASSISTED_LIVING_RFG" not in modalities\n        and "SKILLED_NURSING" not in modalities\n    )\n    if pure_independent:\n        disciplinary_order = 0\n        grade_order = 0\n        counts = {}\n    else:\n        disciplinary = _upper(history.get("disciplinary_action"))\n        disciplinary_order = 0 if disciplinary == "N" else (2 if disciplinary == "Y" else 1)\n        counts = history.get("grade_counts") if isinstance(history.get("grade_counts"), dict) else {}\n        latest_grade = _upper(history.get("latest_known_grade"))\n        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "UNKNOWN": 4}.get(latest_grade, 4)\n\n    return (\n'''
if old not in text:
    raise SystemExit('modalities block not found')
text = text.replace(old, new, 1)
path.write_text(text)

data_path = Path('data/nevada/verified/provider_housing_primary_evidence.json')
payload = json.loads(data_path.read_text())
records = payload.setdefault('records', [])
if not any(r.get('record_key') == 'RED_ROCK_POINTE_RETIREMENT' for r in records):
    records.append({
        "record_key": "RED_ROCK_POINTE_RETIREMENT",
        "community_name": "Red Rock Pointe Retirement Community",
        "aliases": ["Red Rock Pointe", "Red Rock Pointe Retirement", "Red Rock Pointe Retirement Community"],
        "address": "4445 S Grand Canyon Dr",
        "city": "Las Vegas",
        "state": "NV",
        "zip": "89147",
        "append_as_canonical": True,
        "canonical_id": "NV-PROVIDER-IL-RED-ROCK-POINTE",
        "canonical_type": "INDEPENDENT_LIVING",
        "housing_modalities": ["INDEPENDENT_LIVING"],
        "primary_source_url": "https://rlcommunities.com/communities/nevada/red-rock-pointe-retirement/",
        "evidence": {
            "independent_living_verified": True,
            "social_engagement_verified": True,
            "transportation_verified": True,
            "dining_verified": True,
            "housekeeping_verified": True,
            "outside_care_allowed_verified": True,
            "month_to_month_verified": True,
            "emergency_alert_verified": True,
            "three_meals_daily_verified": True,
            "no_buy_in_fee_verified": True
        },
        "evidence_summary": "Resort Lifestyle Communities identifies Red Rock Pointe at 4445 S Grand Canyon Drive as an all-inclusive independent senior living community with three daily meals, housekeeping, scheduled transportation, daily social programming, emergency alert service, month-to-month rent with no buy-in fee, and the option to contract with third-party in-home healthcare providers if future support is needed."
    })
data_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')

test_path = Path('backend/tests/test_decision_quality_market_and_regulatory.py')
test_path.write_text('''from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent, intent_rank_key\n\n\ndef _intent(query: str):\n    return build_client_intent({}, query, {"signals": {}, "household": {}}, {"signals": {}})\n\n\ndef test_unqualified_las_vegas_search_includes_henderson_valley_option():\n    intent = _intent("Looking for senior living in Las Vegas")\n    row = {"city": "Henderson", "state": "NV", "canonical_type": "INDEPENDENT_LIVING", "housing_modalities": ["INDEPENDENT_LIVING"]}\n    fit = evaluate_candidate_intent(row, intent)\n    assert "LAS_VEGAS" in fit["must_pass"]\n    assert fit["hard_gate"] != "FAIL"\n\n\ndef test_explicit_city_limits_still_excludes_henderson():\n    intent = _intent("Looking only within Las Vegas city limits")\n    row = {"city": "Henderson", "state": "NV", "canonical_type": "INDEPENDENT_LIVING", "housing_modalities": ["INDEPENDENT_LIVING"]}\n    fit = evaluate_candidate_intent(row, intent)\n    assert "LAS_VEGAS_CITY_LIMITS" in fit["must_fail"]\n    assert fit["hard_gate"] == "FAIL"\n\n\ndef _rank_row(name: str, canonical_type: str, modalities, history):\n    return {\n        "facility_name": name,\n        "canonical_type": canonical_type,\n        "housing_modalities": modalities,\n        "care_setting_fit": {"status": "POSSIBLE_FIT"},\n        "client_intent_fit": {\n            "hard_gate": "PASS", "nice_match": [], "nice_fit_scores": {},\n            "public_reputation": {}, "relevant_evidence_known_count": 1,\n            "relevant_evidence_unknown_count": 0,\n        },\n        "regulatory_history": history,\n    }\n\n\ndef test_non_applicable_rfg_grade_does_not_penalize_pure_independent_living():\n    pure_il = _rank_row("Pure IL", "INDEPENDENT_LIVING", ["INDEPENDENT_LIVING"], {})\n    licensed_hybrid = _rank_row(\n        "Licensed Hybrid", "ASSISTED_LIVING_RFG", ["INDEPENDENT_LIVING", "ASSISTED_LIVING"],\n        {"disciplinary_action": "N", "latest_known_grade": "A", "grade_counts": {"A": 1}},\n    )\n    assert intent_rank_key(pure_il)[:-1] == intent_rank_key(licensed_hybrid)[:-1]\n''')
