from app.services.public_quality_display import build_public_quality


def test_alis_history_is_described_not_scored():
    q = build_public_quality({"regulatory_history": {"latest_known_grade": "A", "latest_known_grade_date": "03/19/2026 10:30 AM", "grade_counts": {"A": 7, "B": 2, "C": 0, "D": 0}, "known_grade_count": 9, "inspection_count": 10, "disciplinary_action": "N", "source_url": "https://x"}})
    assert q["kind"] == "NV_STATE_INSPECTION" and q["latest_grade"] == "A" and q["latest_grade_date"] == "03/19/2026"
    assert q["grades_below_a"] == {"B": 2} and q["disciplinary_action_on_record"] is False
    assert "satisfaction" in q["caveat"]


def test_unknown_grade_is_not_a_grade():
    q = build_public_quality({"regulatory_history": {"latest_known_grade": "UNKNOWN", "latest_known_grade_date": "UNKNOWN", "grade_counts": {"A": 0, "B": 0, "C": 0, "D": 0}, "known_grade_count": 0, "inspection_count": 0}})
    assert q["latest_grade"] is None and q["latest_grade_date"] is None and q["graded_inspections"] == 0


def test_cms_ratings_keep_their_own_scale():
    q = build_public_quality({}, {"cms_ccn": "295076", "cms_overall_rating": "2", "cms_health_inspection_rating": "1", "cms_staffing_rating": "3", "cms_quality_measure_rating": "5", "cms_processing_date": "2026-08-01"})
    assert q["kind"] == "CMS_FIVE_STAR" and q["overall"] == 2 and q["health_inspection"] == 1 and q["as_of"] == "2026-08-01"
    assert "grade" not in q


def test_missing_rating_is_no_record_not_a_low_rating():
    assert build_public_quality({}, {"cms_ccn": "295067", "cms_overall_rating": ""})["kind"] == "NONE"
    none = build_public_quality({}, None)
    assert none["kind"] == "NONE" and "not a negative finding" in none["statement"]
