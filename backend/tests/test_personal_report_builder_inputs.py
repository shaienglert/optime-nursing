import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_input_surface_is_closed():
    assert list(inspect.signature(build_personal_report_payload).parameters) == ["result", "case_claims", "research_claims", "facility_claims"]
