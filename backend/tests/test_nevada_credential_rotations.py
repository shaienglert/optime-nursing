from scripts.refresh_nevada_registry import analyze_credential_rotations


def test_same_base_and_address_is_probable_renewal():
    old = [{"credential_number": "10013-AGC-6", "address": "123 Main St"}]
    new = [{"credential_number": "10013-AGC-7", "address": "123 MAIN ST."}]
    result = analyze_credential_rotations(old, new)
    assert result["probable_renewals_count"] == 1
    assert result["unmatched_removed_count"] == 0
    assert result["unmatched_added_count"] == 0


def test_different_address_must_not_merge():
    old = [{"credential_number": "10013-AGC-6", "address": "123 Main St"}]
    new = [{"credential_number": "10013-AGC-7", "address": "999 Other Rd"}]
    result = analyze_credential_rotations(old, new)
    assert result["probable_renewals_count"] == 0
    assert result["unmatched_removed_count"] == 1


def test_missing_address_must_not_merge():
    old = [{"credential_number": "10013-AGC-6", "address": ""}]
    new = [{"credential_number": "10013-AGC-7", "address": ""}]
    assert analyze_credential_rotations(old, new)["probable_renewals_count"] == 0
