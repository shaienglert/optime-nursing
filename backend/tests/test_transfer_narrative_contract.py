from app.services.patient_decision_engine import build_patient_needs_profile

def test_stated_transfer_need_is_high():
    profile = build_patient_needs_profile({}, "She needs one person to help her get in and out of bed and the shower.")
    needs = {n['parameter_id']: n for n in profile['needs']}
    assert needs['transfer_assistance']['requirement_level'] == 'HIGH'

def test_negated_transfer_need_is_not_added():
    profile = build_patient_needs_profile({}, "She does not need one person to help her get in and out of bed and the shower.")
    assert 'transfer_assistance' not in {n['parameter_id'] for n in profile['needs']}
