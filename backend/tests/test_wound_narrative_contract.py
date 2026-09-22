from app.services.patient_decision_engine import build_patient_needs_profile

def test_stated_wound_need_is_high():
    profile = build_patient_needs_profile({}, "pressure wound on her heel that needs daily dressing changes")
    needs = {n['parameter_id']: n for n in profile['needs']}
    assert needs['wound_care']['requirement_level'] == 'HIGH'

def test_negated_wound_need_is_not_added():
    profile = build_patient_needs_profile({}, "She has no pressure wound and does not need dressing changes.")
    assert 'wound_care' not in {n['parameter_id'] for n in profile['needs']}
