from app.services.provider_housing_runtime import _provider_identity_matches, _norm, _norm_addr


def _match(row, record):
    return _provider_identity_matches(
        row,
        record,
        str(row.get("canonical_facility_id") or ""),
        _norm(row.get("facility_name")),
        _norm_addr(row.get("address")),
    )


def test_shared_address_does_not_transfer_capabilities_between_entities():
    row = {
        "canonical_facility_id": "LICENSE-B",
        "facility_name": "Campus Skilled Nursing",
        "address": "100 Main St Suite 200",
        "city": "Las Vegas",
        "state": "NV",
        "zip": "89101",
    }
    record = {
        "canonical_facility_ids": ["LICENSE-A"],
        "community_name": "Campus Assisted Living",
        "aliases": [],
        "address": "100 Main St Suite 100",
        "city": "Las Vegas",
        "state": "NV",
        "zip": "89101",
    }
    assert _match(row, record) is False


def test_governed_canonical_id_still_matches():
    row = {
        "canonical_facility_id": "LICENSE-A",
        "facility_name": "Licensed Name",
        "address": "100 Main St",
        "city": "Las Vegas",
        "state": "NV",
    }
    record = {
        "canonical_facility_ids": ["LICENSE-A"],
        "community_name": "Provider Brand Name",
        "address": "100 Main St",
        "city": "Las Vegas",
        "state": "NV",
    }
    assert _match(row, record) is True
