from app.services.provider_organization_registry import (
    IMAGE_BRAND_ASSET,
    IMAGE_CORP_STOCK,
    IMAGE_FACILITY_SPECIFIC,
    IMAGE_ORG_SHARED,
    REL_OPERATOR,
    REL_OWNER,
    build_organization_id,
    build_provider_organization_registry,
    classify_shared_image,
    expected_displayable_coverage,
    match_location_candidate,
    verify_domain_signals,
)


def _facility(
    canonical_id: str,
    *,
    name: str = "Sample Facility",
    city: str = "Las Vegas",
    state: str = "NV",
    operator: str = "Alpha Care Group",
    owner: str = "Alpha Care Group",
) -> dict:
    return {
        "canonical_id": canonical_id,
        "facility_name": name,
        "city": city,
        "state": state,
        "zip": "89109",
        "phone": "7025550100",
        "operator_name": operator,
        "owner_name": owner,
        "source_retrieved_at": "2026-08-04T00:00:00Z",
    }


def _pilot(canonical_id: str, url: str = "https://alpha-care.com/location") -> dict:
    return {
        "canonical_facility_id": canonical_id,
        "official_website_url": url,
        "official_facility_page_url": url,
        "identity_status": "VERIFIED",
    }


def test_facility_linked_to_verified_operator() -> None:
    facilities = [_facility("CMS-1")]
    pilot = {"CMS-1": _pilot("CMS-1")}
    payload = build_provider_organization_registry(facilities=facilities, pilot_records=pilot)
    links = payload["facility_relationships"]
    assert any(row["relationship_type"] == REL_OPERATOR for row in links)


def test_owner_differs_from_operator_and_is_preserved() -> None:
    facilities = [_facility("CMS-2", operator="Alpha Operations LLC", owner="Alpha Holdings LLC")]
    pilot = {"CMS-2": _pilot("CMS-2")}
    payload = build_provider_organization_registry(facilities=facilities, pilot_records=pilot)
    links = payload["facility_relationships"]
    assert any(row["relationship_type"] == REL_OPERATOR for row in links)
    assert any(row["relationship_type"] == REL_OWNER for row in links)


def test_independent_facility_supported() -> None:
    facilities = [_facility("CMS-3", operator="", owner="")]
    payload = build_provider_organization_registry(facilities=facilities, pilot_records={})
    assert payload["independent_facility_count"] == 1
    assert payload["record_count"] == 0


def test_stable_organization_id_for_rename_does_not_change_when_domain_stable() -> None:
    old = {"legal_name": "Alpha Care Group LLC", "state": "NV", "official_domain": "alpha-care.com"}
    new = {"legal_name": "Alpha Care Holdings LLC", "state": "NV", "official_domain": "alpha-care.com"}
    assert build_organization_id(old) == build_organization_id(new)


def test_same_name_unrelated_organizations_not_auto_merged_when_state_differs() -> None:
    a = _facility("CMS-4", state="NV", operator="Sunrise Care", owner="Sunrise Care")
    b = _facility("CMS-5", state="AZ", operator="Sunrise Care", owner="Sunrise Care")
    payload = build_provider_organization_registry(facilities=[a, b], pilot_records={})
    assert payload["record_count"] == 2


def test_chain_homepage_multiple_locations_requires_location_signals() -> None:
    match = match_location_candidate(
        facility_name="Sunrise Rehab Center",
        city="Las Vegas",
        zip_code="89109",
        phone="7025550100",
        candidate_text="Find all locations nationwide",
        candidate_url="https://sunrise.com/locations/",
    )
    assert match["matched"] is False


def test_exact_location_page_match_is_accepted() -> None:
    match = match_location_candidate(
        facility_name="Sunrise Rehab Center",
        city="Las Vegas",
        zip_code="89109",
        phone="7025550100",
        candidate_text="Sunrise Rehab Center Las Vegas NV 89109 Call 702-555-0100",
        candidate_url="https://sunrise.com/locations/las-vegas",
    )
    assert match["matched"] is True


def test_wrong_location_page_rejected() -> None:
    match = match_location_candidate(
        facility_name="Sunrise Rehab Center",
        city="Las Vegas",
        zip_code="89109",
        phone="7025550100",
        candidate_text="Sunrise Rehab Center Reno NV 89501 Call 775-555-0100",
        candidate_url="https://sunrise.com/locations/reno",
    )
    assert match["matched"] is False


def test_shared_hero_rejected_as_org_shared() -> None:
    status = classify_shared_image(reuse_count=3, has_location_evidence=False, stock_like=False, logo_like=False)
    assert status == IMAGE_ORG_SHARED


def test_facility_specific_photo_accepted_when_location_evidence_exists() -> None:
    status = classify_shared_image(reuse_count=1, has_location_evidence=True, stock_like=False, logo_like=False)
    assert status == IMAGE_FACILITY_SPECIFIC


def test_logo_and_stock_classification() -> None:
    assert classify_shared_image(reuse_count=1, has_location_evidence=False, stock_like=False, logo_like=True) == IMAGE_BRAND_ASSET
    assert classify_shared_image(reuse_count=1, has_location_evidence=False, stock_like=True, logo_like=False) == IMAGE_CORP_STOCK


def test_domain_verification_requires_two_strong_signals() -> None:
    verified, signals = verify_domain_signals(
        legal_or_brand_name_on_site=True,
        exact_corporate_address_or_phone=False,
        official_corporate_registration_link=False,
        facility_directory_match=False,
        structured_org_data=False,
        authoritative_ownership_link=False,
    )
    assert verified is False
    verified2, signals2 = verify_domain_signals(
        legal_or_brand_name_on_site=True,
        exact_corporate_address_or_phone=False,
        official_corporate_registration_link=False,
        facility_directory_match=True,
        structured_org_data=False,
        authoritative_ownership_link=True,
    )
    assert verified2 is True
    assert len(signals2) >= 2


def test_idempotent_registry_rebuild() -> None:
    facilities = [_facility("CMS-6")]
    pilot = {"CMS-6": _pilot("CMS-6")}
    first = build_provider_organization_registry(facilities=facilities, pilot_records=pilot)
    second = build_provider_organization_registry(facilities=facilities, pilot_records=pilot)
    assert first["record_count"] == second["record_count"]
    assert first["facility_relationship_count"] == second["facility_relationship_count"]


def test_expected_coverage_projection_math() -> None:
    projection = expected_displayable_coverage(baseline_verified_images=0, total_facilities=42, projected_additional_verified=5)
    assert projection["projected_verified_images"] == 5
    assert projection["projected_coverage_percent"] > 0
