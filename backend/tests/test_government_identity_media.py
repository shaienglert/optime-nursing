from app.services.government_identity_media import (
    assess_identity_change,
    build_authoritative_identity,
    count_image_reuse,
    evaluate_image_candidate,
    generate_search_queries,
    merge_registry_records,
    prioritize_facilities,
    verify_official_candidate,
)


def identity() -> dict:
    return {
        "legal_name": "Riverside Care Center",
        "dba": "Riverside Health and Rehab",
        "street_address": "100 Main Street",
        "city": "Orlando",
        "state": "FL",
        "zip_code": "32801",
        "public_phone": "407-555-0100",
        "operator_name": "Trusted Care Group",
        "license_number": "SNF123",
        "cms_certification_number": "105999",
        "known_aliases": [],
    }


def official_page(name: str = "Riverside Care Center") -> str:
    return f"{name} | 100 Main Street, Orlando, FL 32801 | Call 407-555-0100"


def exterior(**overrides: object) -> dict:
    image = {
        "url": "https://riversidecare.com/images/riverside-exterior.jpg",
        "alt_text": "Riverside Care Center exterior building",
        "official_source": True,
        "official_terms_allow_display": True,
        "reachable": True,
    }
    image.update(overrides)
    return image


def test_authoritative_identity_preserves_sources_dates_and_conflicts() -> None:
    canonical = {
        "canonical_id": "CMS-105999",
        "facility_name": "Riverside Care Center",
        "address": "100 Main Street",
        "city": "Orlando",
        "state": "FL",
        "zip": "32801",
        "phone": "4075550100",
        "source_retrieved_at": "2026-07-01T00:00:00Z",
        "source_identity_ids": {"cms_ccn": "105999", "npi": "1234567890"},
        "source_evidence": {"nppes": {"address_1": "200 Other Street", "source_retrieved_at": "2026-07-02T00:00:00Z"}},
    }
    result = build_authoritative_identity(canonical)
    assert result["authoritative_identity_sources"]["legal_name"][0]["retrieved_at"] == "2026-07-01T00:00:00Z"
    assert any(item["field"] == "street_address" for item in result["identity_conflicts"])


def test_query_generation_uses_precise_authoritative_combinations() -> None:
    queries = generate_search_queries(identity())
    assert '"Riverside Care Center" "100 Main Street"' in queries
    assert '"Riverside Health and Rehab" "407-555-0100"' in queries
    assert '"105999" "Official Website"' in queries


def test_exact_government_identity_leads_to_exact_official_page() -> None:
    result = verify_official_candidate(identity(), candidate_url="https://riversidecare.com/location", page_text=official_page(), search_rank=9)
    assert result["status"] == "VERIFIED"
    assert result["official_facility_page_url"].endswith("/location")
    assert result["search_rank_observed"] == 9


def test_similar_name_wrong_facility_is_rejected_even_at_rank_one() -> None:
    result = verify_official_candidate(identity(), candidate_url="https://riversidecare.com/other", page_text="Riverside Care Home, Tampa FL", search_rank=1)
    assert result["verified"] is False
    assert result["rejection_reason"] == "FEWER_THAN_TWO_STRONG_MATCHES"


def test_directory_never_becomes_final_official_source() -> None:
    result = verify_official_candidate(identity(), candidate_url="https://seniorly.com/riverside", page_text=official_page(), search_rank=1)
    assert result["verified"] is False
    assert result["rejection_reason"] == "NON_OFFICIAL_SOURCE_CLASS"


def test_exact_address_and_phone_allow_changed_dba_resolution() -> None:
    verification = verify_official_candidate(identity(), candidate_url="https://riversidecare.com/", page_text=official_page("Riverside Senior Health"))
    change = assess_identity_change(identity(), website_name="Riverside Senior Health", website_address="100 Main Street", website_phone="4075550100", effective_date="2026-01-01")
    assert verification["verified"] is True
    assert change["name_changed"] is True
    assert change["identity_resolved"] is True


def test_operator_homepage_with_multiple_locations_is_not_location_page() -> None:
    result = verify_official_candidate(identity(), candidate_url="https://trustedcare.com/", page_text="Trusted Care Group locations in Florida", is_operator_homepage=True)
    assert result["status"] == "OFFICIAL_OPERATOR_FOUND_LOCATION_UNVERIFIED"
    assert result["official_facility_page_url"] == ""


def test_exact_facility_page_valid_exterior_is_verified() -> None:
    result = evaluate_image_candidate(exterior(), official_facility_page_url="https://riversidecare.com/location", exact_location_verified=True)
    assert result["image_status"] == "VERIFIED"
    assert result["image_category"] == "exterior"


def test_operator_wide_shared_hero_image_is_rejected() -> None:
    shared = exterior(file_hash="abc123")
    reuse = count_image_reuse([shared, {**shared, "url": "https://trustedcare.com/other.jpg"}])
    result = evaluate_image_candidate(shared, official_facility_page_url="https://riversidecare.com/location", exact_location_verified=True, reuse_count=reuse["abc123"])
    assert result["rejection_reason"] == "CORPORATE_OR_STOCK_IMAGE"


def test_stock_lifestyle_image_is_rejected() -> None:
    result = evaluate_image_candidate(exterior(url="https://riversidecare.com/images/pexels-resident.jpg", alt_text="resident lifestyle"), official_facility_page_url="https://riversidecare.com/location", exact_location_verified=True)
    assert result["image_status"] == "REJECTED"


def test_logo_only_page_is_rejected() -> None:
    result = evaluate_image_candidate(exterior(url="https://riversidecare.com/logo.png", alt_text="Riverside logo"), official_facility_page_url="https://riversidecare.com/location", exact_location_verified=True)
    assert result["rejection_reason"] == "INELIGIBLE_CONTENT_LOGO"


def test_broken_image_is_rejected() -> None:
    result = evaluate_image_candidate(exterior(reachable=False), official_facility_page_url="https://riversidecare.com/location", exact_location_verified=True)
    assert result["rejection_reason"] == "BROKEN_IMAGE"


def test_licensing_uncertainty_is_provisional_and_not_displayable() -> None:
    result = evaluate_image_candidate(exterior(official_terms_allow_display=False), official_facility_page_url="https://riversidecare.com/location", exact_location_verified=True)
    assert result["image_status"] == "PROVISIONAL"
    assert result["verified_facility_specific"] is False


def test_renamed_moved_and_closed_facility_states() -> None:
    renamed = assess_identity_change(identity(), website_name="Riverside Senior Health", website_address="100 Main Street", website_phone="4075550100")
    moved = assess_identity_change(identity(), website_name="Riverside Care Center", website_address="900 New Road", website_phone="4075550100")
    closed = assess_identity_change(identity(), website_status="permanently closed")
    assert renamed["identity_resolved"] is True
    assert moved["conflict_notes"] == "MOVED_FACILITY"
    assert closed["conflict_notes"] == "CLOSED_FACILITY"


def test_conflicting_phone_blocks_verification() -> None:
    page = "Riverside Care Center | 100 Main Street, Orlando, FL 32801 | Call 407-555-9999"
    result = verify_official_candidate(identity(), candidate_url="https://riversidecare.com/", page_text=page)
    assert result["verified"] is False
    assert "public_phone" in result["identity_conflicts"]


def test_pipeline_resume_priority_is_configured_and_not_hardcoded() -> None:
    facilities = [
        {"canonical_facility_id": "A", "facility_name": "A", "address": "1 A", "city": "Alpha", "state": "TX"},
        {"canonical_facility_id": "B", "facility_name": "B", "address": "1 B", "city": "Beta", "state": "NV"},
        {"canonical_facility_id": "C", "facility_name": "C", "address": "1 C", "city": "Gamma", "state": "FL"},
    ]
    ordered = prioritize_facilities(facilities, recommendation_ids=["C"], launch_markets=["Beta"])
    assert [item["canonical_facility_id"] for item in ordered] == ["C", "B", "A"]


def test_registry_merge_is_backward_compatible_and_idempotent() -> None:
    legacy = [{"canonical_facility_id": "A", "image_status": "UNKNOWN", "legacy_field": "preserved"}]
    update = [{"canonical_facility_id": "A", "image_status": "VERIFIED", "pipeline_version": "government-identity-media-v1"}]
    once = merge_registry_records(legacy, update)
    twice = merge_registry_records(once, update)
    assert once == twice
    assert once[0]["legacy_field"] == "preserved"
