from __future__ import annotations

import json
import sys
from pathlib import Path
from copy import deepcopy


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.chief_ai_supervisor import evaluate_platform_registry_work_request
from app.services.agent_knowledge_reports import refresh_all_agent_reports
from app.services.platform_registry_service import (
    build_platform_registry_payload,
    evaluate_capability_assignment,
    evaluate_objective_activation_request,
    run_platform_registry_self_audit,
    write_platform_registry_artifacts,
)


class _BlockedDb:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        return None

    def query(self, *args, **kwargs):
        raise AssertionError("blocked work should not reach database queries")


def _payload_with_current_work(payload: dict, capability_id: str) -> dict:
    updated = deepcopy(payload)
    capability = next(cap for cap in updated["capabilities"] if cap["id"] == capability_id)
    updated["summary"]["current_active_objective"] = "test_objective"
    updated["summary"]["current_executable_capability"] = capability_id
    updated["summary"]["current_blocker"] = None
    updated["self_audit"] = {"has_p0_findings": False, "findings": [], "registry_trust_verdict": "REGISTRY_TRUSTED"}
    updated["integrity_findings"] = []
    updated["objective_stack"] = {
        "objective_id": "test_objective",
        "name": "Test Objective",
        "required_capabilities": [capability_id],
        "current_work": capability_id,
        "current_blocker": None,
        "assigned_agent": capability.get("owner"),
        "current_task": capability.get("next_action"),
    }
    updated["objective_dashboards"] = [updated["objective_stack"]]
    return updated


def test_platform_registry_builds_objective_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.platform_registry_service.DATABASE_PATH", tmp_path / "platform_registry.json")
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_MD_PATH", tmp_path / "PLATFORM_REGISTRY.md")
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_JSON_PATH", tmp_path / "PLATFORM_REGISTRY.json")

    payload = build_platform_registry_payload()
    assert payload["summary"]["objectives_discovered"] >= 5
    assert payload["summary"]["current_active_objective"] == "launch_nevada"
    assert payload["summary"]["current_executable_capability"] == "source_intelligence"
    assert payload["objective_stack"]["current_work"] == "source_intelligence"
    assert len(payload["objective_dashboards"]) >= 5
    assert payload["registry_trust_verdict"] in {"REGISTRY_TRUSTED", "REGISTRY_PARTIALLY_TRUSTED", "REGISTRY_NOT_TRUSTED"}
    assert payload["summary"]["current_blocker"] == "source_intelligence"
    assert payload["summary"]["current_assigned_agent"] == "OPTIME Source Intelligence"
    assert payload["summary"]["current_task"] == "Complete the remaining approved source integrations and unblock market build coverage."
    assert len(payload["capabilities"]) == 28
    assert len(payload["objective_dashboards"]) == 6


def test_platform_registry_assignment_allows_ready_capability() -> None:
    decision = evaluate_platform_registry_work_request("source_intelligence")
    assert decision["allowed"] is True
    assert decision["current_active_objective"] == "launch_nevada"
    assert decision["current_executable_capability"] == "source_intelligence"


def test_platform_registry_assignment_rejects_and_records_incident() -> None:
    fake_db = _BlockedDb()
    decision = evaluate_platform_registry_work_request("email_delivery", db=fake_db, agent_key="email_delivery", domain="Operations")
    assert decision["allowed"] is False
    assert decision["reason"] == "NOT_CURRENT_OBJECTIVE"
    assert decision["suggested_prerequisite"] is not None
    assert fake_db.added
    assert getattr(fake_db.added[0], "incident_type", "") == "REGISTRY_ASSIGNMENT_REJECTED"


def test_refresh_all_agent_reports_blocks_before_workflow(monkeypatch) -> None:
    fake_db = _BlockedDb()
    monkeypatch.setattr("app.services.agent_knowledge_reports.AGENT_REPORT_DEFS", [
        {
            "agent_key": "provider_intelligence",
            "agent_name": "Provider Intelligence Agent",
            "domain": "Provider verified capabilities",
        }
    ])
    called = {"workflow": False}

    def _fail_workflow(*args, **kwargs):
        called["workflow"] = True
        raise AssertionError("blocked work should not start a workflow")

    monkeypatch.setattr("app.services.agent_knowledge_reports._run_agent_workflow", _fail_workflow)
    result = refresh_all_agent_reports(fake_db, refresh_mode="manual", agent_keys=["provider_intelligence"])
    assert result["failures"] == 1
    assert called["workflow"] is False
    assert any(getattr(obj, "incident_type", "") == "REGISTRY_ASSIGNMENT_REJECTED" for obj in fake_db.added)


def test_platform_registry_write_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.platform_registry_service.DATABASE_PATH", tmp_path / "platform_registry.json")
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_MD_PATH", tmp_path / "PLATFORM_REGISTRY.md")
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_JSON_PATH", tmp_path / "PLATFORM_REGISTRY.json")

    payload = write_platform_registry_artifacts()
    assert (tmp_path / "platform_registry.json").exists()
    assert (tmp_path / "PLATFORM_REGISTRY.md").exists()
    assert (tmp_path / "PLATFORM_REGISTRY.json").exists()
    loaded = json.loads((tmp_path / "platform_registry.json").read_text(encoding="utf-8"))
    assert loaded["summary"]["objectives_discovered"] == payload["summary"]["objectives_discovered"]
    assert loaded["current_blocking_capability"] == payload["current_blocking_capability"]


def test_required_build_dependency_blocks_work(monkeypatch) -> None:
    payload = _payload_with_current_work(build_platform_registry_payload(), "canonical_universe")
    for capability in payload["capabilities"]:
        if capability["id"] == "market_builder":
            capability["verification_status"] = "NOT_STARTED"
            capability["production_readiness"] = "BLOCKED"
            capability["acceptance_contract"]["acceptance_status"] = "UNVERIFIED"
    monkeypatch.setattr("app.services.platform_registry_service.load_platform_registry", lambda: payload)
    decision = evaluate_capability_assignment("canonical_universe")
    assert decision["allowed"] is False
    assert decision["reason"] == "DEPENDENCY_BLOCKED"
    assert decision["suggested_prerequisite"] == "market_builder"
    assert decision["dependency_block_type"] == "REQUIRED_BUILD_DEPENDENCY"


def test_required_runtime_dependency_blocks_execution(monkeypatch) -> None:
    payload = _payload_with_current_work(build_platform_registry_payload(), "matching_improvement")
    for capability in payload["capabilities"]:
        if capability["id"] == "matching_improvement":
            capability["required_runtime_dependencies"] = ["runtime_sync"]
            capability["dependencies"] = capability["required_build_dependencies"] + capability["required_runtime_dependencies"] + capability["evidence_dependencies"]
        if capability["id"] == "runtime_sync":
            capability["production_readiness"] = "BLOCKED"
    monkeypatch.setattr("app.services.platform_registry_service.load_platform_registry", lambda: payload)
    decision = evaluate_capability_assignment("matching_improvement")
    assert decision["allowed"] is False
    assert decision["reason"] == "DEPENDENCY_BLOCKED"
    assert decision["suggested_prerequisite"] == "runtime_sync"
    assert decision["dependency_block_type"] == "REQUIRED_RUNTIME_DEPENDENCY"


def test_evidence_dependency_blocks_only_evidence_output(monkeypatch) -> None:
    payload = _payload_with_current_work(build_platform_registry_payload(), "narrative_intelligence")
    for capability in payload["capabilities"]:
        if capability["id"] == "clinical_evidence":
            capability["verification_status"] = "IN_PROGRESS"
            capability["production_readiness"] = "BLOCKED"
            capability["acceptance_contract"]["acceptance_status"] = "UNVERIFIED"
    monkeypatch.setattr("app.services.platform_registry_service.load_platform_registry", lambda: payload)
    gated = evaluate_capability_assignment("narrative_intelligence", require_evidence=True, requested_output="EVIDENCE_DEPENDENT_OUTPUT")
    general = evaluate_capability_assignment("narrative_intelligence", require_evidence=False, requested_output="GENERAL")
    assert gated["allowed"] is False
    assert gated["reason"] == "DEPENDENCY_BLOCKED"
    assert gated["dependency_block_type"] == "EVIDENCE_DEPENDENCY"
    assert general["allowed"] is True
    assert general["reason"] == "ALLOWED"


def test_optional_consumer_does_not_block_producer(monkeypatch) -> None:
    payload = _payload_with_current_work(build_platform_registry_payload(), "activities_intelligence")
    for capability in payload["capabilities"]:
        if capability["id"] == "narrative_intelligence":
            capability["production_readiness"] = "BLOCKED"
            capability["verification_status"] = "IN_PROGRESS"
    monkeypatch.setattr("app.services.platform_registry_service.load_platform_registry", lambda: payload)
    decision = evaluate_capability_assignment("activities_intelligence")
    assert decision["allowed"] is True
    assert decision["reason"] == "ALLOWED"


def test_monitoring_relationship_does_not_block_supervisor(monkeypatch) -> None:
    payload = _payload_with_current_work(build_platform_registry_payload(), "chief_ai_supervisor")
    payload["registry_trust_verdict"] = "REGISTRY_TRUSTED"
    runtime_dependencies = set()
    for capability in payload["capabilities"]:
        if capability["id"] == "chief_ai_supervisor":
            runtime_dependencies = set(capability.get("required_runtime_dependencies") or [])
    for capability in payload["capabilities"]:
        if capability["id"] in runtime_dependencies:
            capability["verification_status"] = "VERIFIED"
            capability["production_readiness"] = "PRODUCTION_READY"
            if isinstance(capability.get("acceptance_contract"), dict):
                capability["acceptance_contract"]["acceptance_status"] = "VERIFIED"
        if capability["id"] == "market_builder":
            capability["production_readiness"] = "BLOCKED"
            capability["verification_status"] = "NOT_STARTED"
            capability["acceptance_contract"]["acceptance_status"] = "UNVERIFIED"
    monkeypatch.setattr("app.services.platform_registry_service.load_platform_registry", lambda: payload)
    decision = evaluate_capability_assignment("chief_ai_supervisor")
    assert decision["allowed"] is True
    assert decision["reason"] == "ALLOWED"


def test_documentation_reference_never_blocks_execution(monkeypatch) -> None:
    payload = _payload_with_current_work(build_platform_registry_payload(), "source_intelligence")
    for capability in payload["capabilities"]:
        if capability["id"] == "source_intelligence":
            capability["documentation_references"] = ["reports/DOES_NOT_EXIST.md"]
    monkeypatch.setattr("app.services.platform_registry_service.load_platform_registry", lambda: payload)
    decision = evaluate_capability_assignment("source_intelligence")
    assert decision["allowed"] is True
    assert decision["reason"] == "ALLOWED"


def test_self_audit_detects_circular_required_dependencies() -> None:
    payload = build_platform_registry_payload()
    for capability in payload["capabilities"]:
        if capability["id"] == "provider_intelligence":
            capability["required_build_dependencies"] = ["activities_intelligence"]
        if capability["id"] == "activities_intelligence":
            capability["required_build_dependencies"] = ["provider_intelligence"]
    audit = run_platform_registry_self_audit(payload)
    assert any(finding["finding_type"] == "CIRCULAR_REQUIRED_DEPENDENCY" for finding in audit["findings"])


def test_self_audit_detects_duplicate_responsibility() -> None:
    payload = build_platform_registry_payload()
    payload["capabilities"][0]["canonical_responsibility"] = payload["capabilities"][1]["canonical_responsibility"]
    audit = run_platform_registry_self_audit(payload)
    assert any(finding["finding_type"] == "DUPLICATE_CANONICAL_RESPONSIBILITY" for finding in audit["findings"])


def test_self_audit_rejects_multiple_active_objectives(monkeypatch) -> None:
    from app.services import platform_registry_service

    mutated = deepcopy(platform_registry_service.OBJECTIVE_CATALOG)
    mutated[1]["activation_status"] = "ACTIVE"
    monkeypatch.setattr(platform_registry_service, "OBJECTIVE_CATALOG", mutated)
    audit = run_platform_registry_self_audit(build_platform_registry_payload())
    assert any(finding["finding_type"] == "ACTIVE_OBJECTIVE_COUNT_INVALID" for finding in audit["findings"])


def test_non_owner_objective_activation_rejected() -> None:
    decision = evaluate_objective_activation_request("launch_florida", requested_by="SUPERVISOR")
    assert decision["allowed"] is False
    assert decision["reason"] == "OWNER_ONLY_OBJECTIVE_CONTROL"


def test_self_audit_detects_stale_report_disagreement(tmp_path, monkeypatch) -> None:
    payload = build_platform_registry_payload()
    report_json = tmp_path / "PLATFORM_REGISTRY.json"
    report_md = tmp_path / "PLATFORM_REGISTRY.md"
    report_json.write_text(json.dumps({"summary": {"current_active_objective": "stale"}}), encoding="utf-8")
    report_md.write_text("# stale report\n", encoding="utf-8")
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_JSON_PATH", report_json)
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_MD_PATH", report_md)
    audit = run_platform_registry_self_audit(payload)
    assert any(finding["finding_type"] == "STALE_REGISTRY_REPORT_DISAGREEMENT" for finding in audit["findings"])


def test_matching_improvement_remains_canonical_and_unique() -> None:
    payload = build_platform_registry_payload()
    matches = [capability for capability in payload["capabilities"] if capability["id"] == "matching_improvement"]
    assert len(matches) == 1
    assert matches[0]["owner"] == "OPTIME Matching Improvement"
    assert matches[0]["implementation_files"]
    assert all(finding["finding_type"] != "AGENT_MAPPED_TO_MISSING_CAPABILITY" for finding in payload["integrity_findings"])


def test_exact_canonical_counts_and_service_values() -> None:
    payload = build_platform_registry_payload()
    assert len(payload["capabilities"]) == 28
    assert len(payload["objective_dashboards"]) == 6
    assert payload["summary"]["current_blocker"] == "source_intelligence"
    assert payload["summary"]["current_assigned_agent"] == "OPTIME Source Intelligence"
    assert payload["summary"]["current_task"] == "Complete the remaining approved source integrations and unblock market build coverage."


def test_final_canonical_graph_has_zero_missing_and_duplicate_ids() -> None:
    payload = build_platform_registry_payload()
    assert sum(1 for finding in payload["integrity_findings"] if finding["finding_type"] == "MISSING_CAPABILITY_REFERENCE") == 0
    assert sum(1 for finding in payload["integrity_findings"] if finding["finding_type"] == "DUPLICATE_CAPABILITY_ID") == 0


def test_compatibility_projection_matches_typed_dependencies() -> None:
    payload = build_platform_registry_payload()
    for capability in payload["capabilities"]:
        expected = []
        for item in capability.get("required_build_dependencies") or []:
            if item not in expected:
                expected.append(item)
        for item in capability.get("required_runtime_dependencies") or []:
            if item not in expected:
                expected.append(item)
        for item in capability.get("evidence_dependencies") or []:
            if item not in expected:
                expected.append(item)
        assert capability.get("dependencies") == expected


def test_every_objective_milestone_references_valid_capability() -> None:
    payload = build_platform_registry_payload()
    capability_ids = {capability["id"] for capability in payload["capabilities"]}
    for objective in payload["objective_dashboards"]:
        for milestone in objective.get("milestones") or []:
            for capability_id in milestone.get("capability_ids") or []:
                assert capability_id in capability_ids


def test_registry_trust_derives_from_claim_contracts(monkeypatch) -> None:
    from app.services import platform_registry_service

    original = platform_registry_service._derive_platform_claim_contracts

    def _mutated(payload):
        claims = original(payload)
        for claim in claims:
            if claim["claim_id"] == "platform:current_blocker":
                claim["verification_status"] = "PARTIALLY_VERIFIED"
                claim["missing_proof_classes"] = ["test_evidence"]
        return claims

    monkeypatch.setattr(platform_registry_service, "_derive_platform_claim_contracts", _mutated)
    payload = build_platform_registry_payload()
    assert payload["registry_trust_verdict"] == "REGISTRY_PARTIALLY_TRUSTED"


def test_missing_runtime_proof_removes_verified(monkeypatch) -> None:
    from app.services import platform_registry_service

    original = platform_registry_service._capability_runtime_context

    def _mutated(capability):
        if capability.get("id") == "platform_registry":
            return [], "build_platform_registry_payload", None, "CONTROLLED_REPLAY"
        return original(capability)

    monkeypatch.setattr(platform_registry_service, "_capability_runtime_context", _mutated)
    payload = build_platform_registry_payload()
    registry_cap = next(capability for capability in payload["capabilities"] if capability["id"] == "platform_registry")
    assert registry_cap["acceptance_status"] != "VERIFIED"


def test_missing_tests_remove_verified(monkeypatch) -> None:
    from app.services import platform_registry_service

    original = platform_registry_service._capability_test_evidence

    def _mutated(capability):
        if capability.get("id") == "platform_registry":
            return {"direct_tests": [], "indirect_tests": [], "integration_tests": [], "policy_tests": [], "constitutional_tests": []}
        return original(capability)

    monkeypatch.setattr(platform_registry_service, "_capability_test_evidence", _mutated)
    payload = build_platform_registry_payload()
    registry_cap = next(capability for capability in payload["capabilities"] if capability["id"] == "platform_registry")
    assert registry_cap["acceptance_status"] != "VERIFIED"


def test_missing_implementation_removes_verified(monkeypatch) -> None:
    from app.services import platform_registry_service

    mutated = deepcopy(platform_registry_service.CAPABILITY_CATALOG)
    for capability in mutated:
        if capability["id"] == "platform_registry":
            capability["implementation_files"] = []
    monkeypatch.setattr(platform_registry_service, "CAPABILITY_CATALOG", mutated)
    payload = build_platform_registry_payload()
    registry_cap = next(capability for capability in payload["capabilities"] if capability["id"] == "platform_registry")
    assert registry_cap["acceptance_status"] != "VERIFIED"


def test_six_audited_edges_keep_exact_typed_classifications() -> None:
    payload = build_platform_registry_payload()
    capability_index = {capability["id"]: capability for capability in payload["capabilities"]}
    assert "market_builder" in capability_index["canonical_universe"]["required_build_dependencies"]
    assert "narrative_intelligence" in capability_index["activities_intelligence"]["optional_consumers"]
    assert "clinical_evidence" in capability_index["clinical_knowledge"]["evidence_dependencies"]
    assert "clinical_evidence" in capability_index["narrative_intelligence"]["evidence_dependencies"]
    assert "narrative_intelligence" in capability_index["family_experience_intelligence"]["evidence_dependencies"]
    assert "market_builder" in capability_index["chief_ai_supervisor"]["monitoring_relationships"]


def test_registry_service_artifact_values_agree(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.platform_registry_service.DATABASE_PATH", tmp_path / "platform_registry.json")
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_MD_PATH", tmp_path / "PLATFORM_REGISTRY.md")
    monkeypatch.setattr("app.services.platform_registry_service.REPORT_JSON_PATH", tmp_path / "PLATFORM_REGISTRY.json")
    payload = write_platform_registry_artifacts()
    stored = json.loads((tmp_path / "platform_registry.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "PLATFORM_REGISTRY.json").read_text(encoding="utf-8"))
    assert payload["summary"] == stored["summary"] == report["summary"]
    assert payload["registry_trust_verdict"] == stored["registry_trust_verdict"] == report["registry_trust_verdict"]
