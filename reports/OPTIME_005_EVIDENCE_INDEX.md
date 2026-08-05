# OPTIME-005 Evidence Index

This file records the primary repository evidence used by the Master Platform Audit.

## Canonical governance and control

- `AGENTS.md`
- `docs/OPTIME_PRINCIPLES.md`
- `docs/OPTIME_PRINCIPLES_REGISTRY.md`
- `backend/app/services/platform_registry_service.py`
- `backend/app/services/chief_ai_supervisor.py`
- `backend/app/services/remediation_policy_engine.py`
- `backend/app/services/runtime_sync_service.py`

## Source, market, and canonical data

- `backend/app/services/source_lifecycle_service.py`
- `backend/app/services/source_policy_engine.py`
- `backend/app/services/canonical_universe.py`
- `scripts/build_nevada_canonical_universe.py`
- `scripts/run_nevada_authoritative_source_integration.py`
- `reports/SOURCE_LIFECYCLE_STATUS.md`
- `reports/NEVADA_SOURCE_INTEGRATION_REPORT.md`
- `reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md`

## Knowledge, decision, and experience

- `backend/app/services/agent_knowledge_reports.py`
- `backend/app/services/patient_decision_engine.py`
- `frontend/src/app/assessment/page.tsx`
- `frontend/src/components/assessment/assessment-advisor-experience.tsx`

## Runtime and production evidence

- `backend/app/main.py`
- `reports/RELEASE_RECOVERY_LEDGER_OPTIME-001-RLS.json`
- production endpoint evidence documented in OPTIME-003-HF1 and OPTIME-004 results

## Deterministic tests

- `backend/tests/test_platform_registry.py`
- `backend/tests/test_chief_ai_supervisor_operations.py`
- `backend/tests/test_runtime_sync_service.py`
- `backend/tests/test_system_health_service.py`
- `backend/tests/test_nevada_canonical_universe.py`
- `backend/tests/test_patient_decision_engine.py`
- frontend assessment tests where present in `frontend/tests/`

The final audit must distinguish direct repository proof, production proof, and audit inference.