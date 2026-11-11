from coverage_parity_contract import is_additive_coverage_metadata
from approved_unknown_delta import approved_unknown_evidence_delta


def test_only_explicit_coverage_fields_are_additive():
    prefix = "$.run_limit5.decision_intelligence.human_intelligence.user_statement_accounting."
    assert is_additive_coverage_metadata(prefix + "coverage_basis", "added", None, "STATEMENT_CLASSIFICATION_ONLY")
    assert is_additive_coverage_metadata(prefix + "semantic_coverage_percent", "added", None, None)
    assert is_additive_coverage_metadata(prefix + "semantic_coverage_status", "added", None, "NOT_INDEPENDENTLY_VERIFIED")


def test_changed_coverage_values_and_ranking_changes_never_qualify():
    prefix = "$.run_limit5.decision_intelligence.human_intelligence.user_statement_accounting."
    for path, kind, old, new in [
        (prefix + "coverage_basis", "value", "OLD", "STATEMENT_CLASSIFICATION_ONLY"),
        (prefix + "semantic_coverage_percent", "added", None, 100.0),
        (prefix + "semantic_coverage_status", "added", None, "VERIFIED"),
        (prefix + "made_up", "added", None, "ANY"),
        ("$.run_limit5.results[0].match_score", "value", 88, 100),
    ]:
        assert not is_additive_coverage_metadata(path, kind, old, new)


def test_unknown_approval_still_rejects_unrelated_differences():
    before = {"run_limit5": {"results": []}}
    after = {"run_limit5": {"results": []}}
    extra = [("$.run_limit5.results[0].match_score", "value", 80, 99)]
    assert approved_unknown_evidence_delta("budget_medicaid_pending", before, after, extra) == set()
