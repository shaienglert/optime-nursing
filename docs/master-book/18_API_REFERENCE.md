# 18 API Reference

## Purpose
Provide implemented API inventory and usage orientation.

## Current Implementation
- API endpoints extracted from backend/app/main.py.
# API Endpoints (Detected in backend/app/main.py)

- @app.get("/")
- @app.get("/health")
- @app.get("/import-summary", response_model=ImportSummaryOut)
- @app.get("/facilities", response_model=List[FacilityListOut])
- @app.get("/facilities/{id}", response_model=FacilityDetailsOut)
- @app.post("/intelligence/run", response_model=IntelligenceRunSummaryOut)
- @app.get("/intelligence/facilities/{id}", response_model=FacilityIntelligenceProfileOut)
- @app.get("/intelligence/schedule")
- @app.get("/expert-agents/knowledge-reports", response_model=List[AgentKnowledgeReportSummaryOut])
- @app.get("/expert-agents/{agent_key}/knowledge-report", response_model=AgentKnowledgeReportOut)
- @app.get("/expert-agents/knowledge-reports/search", response_model=AgentKnowledgeSearchOut)
- @app.post("/expert-agents/knowledge-reports/refresh", response_model=AgentKnowledgeRefreshOut)
- @app.get("/expert-agents/freshness/states")
- @app.get("/supervisor/overview", response_model=KnowledgeSupervisorOut)
- @app.post("/supervisor/run-cycle")
- @app.get("/supervisor/incidents")
- @app.get("/supervisor/stale-usage")
- @app.post("/recommendation/knowledge-guard", response_model=RecommendationGuardCheckOut)
- @app.post("/human-intelligence", response_model=HumanIntelligenceOut)
- @app.post("/human-intelligence/adaptive-response", response_model=AdaptiveQuestionResponseOut)
- @app.post("/resident-outcomes", response_model=ResidentOutcomeOut)
- @app.get("/validation-feedback", response_model=ValidationFeedbackOut)
- @app.post("/provider/facilities/{facility_id}/activities/import", response_model=ActivityImportOut)
- @app.get("/provider/facilities/{facility_id}/activities/categories", response_model=List[ActivityCategoryOut])
- @app.get("/provider/activity-intelligence/policy")
- @app.post("/provider/facilities/{facility_id}/verification/persist", response_model=ProviderPersistOut)
- @app.get("/provider/facilities/{facility_id}/memory", response_model=FacilityMemoryOut)
- @app.post("/provider/facilities/{facility_id}/identity/register/start", response_model=IdentityRegistrationStartOut)
- @app.post("/provider/facilities/{facility_id}/identity/register/verify", response_model=IdentityVerificationCompleteOut)
- @app.post("/provider/facilities/{facility_id}/identity/license/validate", response_model=LicenseValidationOut)
- @app.post("/provider/identity/access-check", response_model=AccessCheckOut)
- @app.post("/provider/facilities/{facility_id}/identity/field-update", response_model=FieldUpdateOut)
- @app.post("/provider/facilities/{facility_id}/identity/audit/{audit_id}/revert", response_model=RevertAuditOut)
- @app.post("/provider/facilities/{facility_id}/identity/staff/invite", response_model=IdentityRegistrationStartOut)
- @app.post("/provider/facilities/{facility_id}/identity/role/change", response_model=RoleChangeOut)
- @app.post("/provider/identity/reverification/run")


## Architecture
- FastAPI application with ingestion, facility lookup, intelligence, supervisor, verification, and provider identity surfaces.

## Dependencies
- backend/app/main.py
- backend/app/services/*

## Current Status
- Implemented: 36 route decorators detected in source scan.

## Completed Work
- Endpoints exist for health, facilities, intelligence, supervisor, provider identity, and outcomes.

## Remaining Work
- Publish versioned OpenAPI snapshots in docs/master-book for stable external reference.

## Known Limitations
- backend/app/api/facilities.py exists but is empty; endpoint ownership is centralized in main.py.

## Next Implementation Steps
- Split route modules by domain and preserve OpenAPI parity tests.
