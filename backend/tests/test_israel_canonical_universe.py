import json

from app.services.canonical_universe import resolve_canonical_universe_path


def _payload():
    return json.loads(resolve_canonical_universe_path("israel").read_text(encoding="utf-8"))


def test_israel_market_resolves_by_name_and_alias():
    assert resolve_canonical_universe_path("israel") == resolve_canonical_universe_path("IL")


def test_one_record_per_source_row_without_cross_list_merge():
    payload = _payload()
    records = payload["records"]
    assert payload["record_count"] == len(records) == 467
    assert len({r["canonical_id"] for r in records}) == len(records)
    assert all(r["merge_confidence"] == "NOT_MERGED" for r in records)
    settings = {}
    for r in records:
        settings[r["canonical_setting"]] = settings.get(r["canonical_setting"], 0) + 1
    assert settings == {
        "IL_GERIATRIC_NURSING_INSTITUTION": 255,
        "IL_OLD_AGE_HOME": 115,
        "IL_PROTECTED_HOUSING": 97,
    }


def test_every_record_carries_source_evidence():
    for r in _payload()["records"]:
        assert r["source_evidence"], r["canonical_id"]
        for evidence in r["source_evidence"].values():
            assert evidence["source_file"].startswith("data/israel/raw/")


def test_missing_information_stays_unknown_not_negative():
    for r in _payload()["records"]:
        assert r["availability"] == "UNKNOWN"
        if r["canonical_setting"] == "IL_GERIATRIC_NURSING_INSTITUTION":
            assert r["license_id"]
            assert r["moh_code_agreement"] in {"YES", "NO"}
            assert r["functional_levels_served"] == "UNKNOWN"
        else:
            assert r["moh_code_agreement"] == "UNKNOWN"
            assert r["license_id"] is None
