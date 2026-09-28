"""Missing nearby-place information must not act as negative evidence in ranking.

nearby_rank_key used to give every non-KNOWN community (no coordinates, a failed lookup,
outside the POI shortlist) a key that sorted it below every KNOWN community -- including
one confirmed to have nothing the family asked for nearby. Once facility coordinates come
from geocoding, an address the geocoder cannot match would sink a community to the bottom
of its tie group for a reason that says nothing about the community.
"""
from app.services.nearby_place_service import nearby_rank_key


def _known(band: int, avg=None) -> dict:
    return {"nearby_place_fit": {"status": "KNOWN", "fit_band": band, "average_distance_miles": avg}}


def _not_known(status: str) -> dict:
    return {"nearby_place_fit": {"status": status, "reason": "test"}}


def test_unknown_is_neutral_not_last():
    for importance in ("Important", "Nice to have"):
        for status in ("UNKNOWN", "NOT_EVALUATED"):
            key = nearby_rank_key(_not_known(status), importance)
            # Same key as a KNOWN community with nothing nearby: no boost, no penalty.
            assert key == nearby_rank_key(_known(0), importance), (importance, status)


def test_row_without_any_nearby_fit_is_neutral():
    assert nearby_rank_key({}, "Important") == nearby_rank_key(_known(0), "Important")


def test_positive_nearby_evidence_still_ranks_first():
    unknown = nearby_rank_key(_not_known("UNKNOWN"), "Important")
    for band in (1, 2, 3):
        assert nearby_rank_key(_known(band, 2.0), "Important") < unknown, band


def test_stable_order_decides_between_unknown_and_nothing_nearby():
    # Tied on everything else, the pre-existing order must survive: the unknown community
    # that was ahead stays ahead of the one confirmed to have nothing nearby.
    rows = [_not_known("UNKNOWN"), _known(0)]
    ranked = sorted(enumerate(rows), key=lambda pair: (*nearby_rank_key(pair[1], "Important"), pair[0]))
    assert [index for index, _ in ranked] == [0, 1]
