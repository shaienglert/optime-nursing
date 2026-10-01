from app.services.facility_evidence_contract import FacilityFact,availability_fact,license_fact,room_price

def test_provider_fact_is_usable_without_independent_web_confirmation():
    assert FacilityFact("YES","PROVIDER",status="PROVIDER_REPORTED").decision_usable is True

def test_provider_license_is_not_regulatory_verified():
    fact=license_fact("NV-123",regulatory_verified=False)
    assert fact.status=="PROVIDER_REPORTED"
    assert fact.status!="REGULATORY_VERIFIED"

def test_every_availability_direction_requires_direct_verification():
    for value in ("AVAILABLE","LIMITED","WAITLIST","UNAVAILABLE","NO","UNKNOWN"):
        fact=availability_fact(value,source_type="PROVIDER")
        assert fact["final_status"]=="REQUIRES_DIRECT_VERIFICATION"

def test_starting_at_price_is_not_represented_as_exact_total():
    price=room_price(room_type="Studio",base_rent=4450,qualifier="STARTING_AT")
    assert price["pricing_qualifier"]=="STARTING_AT"
    assert price["total_affordability_status"]=="PENDING"

def test_unknown_care_fee_keeps_total_affordability_pending():
    price=room_price(room_type="One Bedroom",base_rent=5200,qualifier="EXACT",care_fee=None,mandatory_monthly_fees=0)
    assert price["total_affordability_status"]=="PENDING"
