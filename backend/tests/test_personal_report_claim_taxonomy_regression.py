from app.services.personal_decision_report_contract import ClaimType


def test_claim_taxonomy_remains_closed():
    assert {c.value for c in ClaimType} == {"USER_INFORMATION", "VERIFIED_FACT", "RESEARCH_FINDING", "ENGINE_CONCLUSION", "UNKNOWN"}
