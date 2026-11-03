from app.services.oomniker_preference_analysis import _enforced_as_must
from app.services.decision_engine_core import _availability_note


def test_free_text_restating_a_must_is_not_an_open_preference():
    assert _enforced_as_must("Kosher", {"KOSHER_MEALS", "ADL_SUPPORT_AVAILABLE"})
    assert not _enforced_as_must("Cultural activities", {"KOSHER_MEALS"})
    assert not _enforced_as_must("Kosher", {"ADL_SUPPORT_AVAILABLE"})


def test_availability_note_says_when_no_space_is_on_record():
    assert "No open space" in _availability_note("NO")
    assert "limited" in _availability_note("LIMITED").lower()
    assert "confirmed directly" in _availability_note("UNKNOWN")
