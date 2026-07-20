# GOVERNED RUNTIME INTEGRATION REPORT

## Scope
- Objective: connect governed decision architecture directly to the production runtime questionnaire -> facilities -> ranking -> results flow.
- Constraint: no parallel recommendation engine and no offline-only recommendation artifacts.
- Truth constraints preserved:
  - EXTERNAL PROFESSIONAL VALIDATION = PARTIAL
  - 52% BENCHMARK STATUS = FAIL

## Runtime Wiring Implemented
- Backend runtime governance context endpoint:
  - `GET /governance/runtime-context` in `backend/app/main.py`
  - Exposes professional rule registry, three-layer model, candidate governance policy, facility evidence runtime summary, canonical reconciliation, confidence status, and validation truth flags.
- Frontend API integration:
  - `fetchGovernanceRuntimeContext()` in `frontend/src/lib/api.ts`
  - Typed contract `GovernanceRuntimeContext` consumed by runtime engine call path.
- Governed runtime model integration:
  - Added `frontend/src/lib/governed-runtime.ts` to produce requirement/evidence/candidate/governance metadata.
  - Integrated into existing `runOptimeV2Engine` in `frontend/src/lib/optime-v2-engine.ts`.
  - Enforced MUST gating (`MUST_FAILED` cannot be surfaced in accepted/displayed lists).
  - Preserved uncertainty (`UNKNOWN` stays `UNKNOWN`; no silent promotion to verified).
  - Prevented pending/unvalidated professional rules from silently creating hard MUST requirements.
- Production results flow wired:
  - `frontend/src/app/results/results-page-client.tsx` now loads governance runtime context together with facilities and passes it into `runOptimeV2Engine`.
  - Existing recommendation cards now show additive governed MUST status details (eligibility, identity, MUST satisfied/failed/unknown, verification required).

## Runtime Validator and Negative Tests
- Added validator script:
  - `scripts/validate_governed_runtime_integration.cjs`
- Validator executes case `POST_STROKE_MIAMI_001` through the runtime engine path and fails on bypass conditions.
- Negative checks enforced:
  - age 80 alone does not become MUST 24/7 nursing
  - social preference does not become MUST
  - unknown budget is not forced to hard zero-budget rejection
  - unknown capability is not converted to YES
  - ranking/legacy weighting cannot override MUST_FAILED
  - unvalidated professional rules cannot create hard MUST
  - missing source cannot become verified/high-confidence evidence

## Executed Evidence
- Command:
  - `node scripts/validate_governed_runtime_integration.cjs`
- Result:
  - STATUS=PASS
  - TOP5=5
  - ERRORS=0
- Artifacts generated:
  - `reports/GOVERNED_RUNTIME_INTEGRATION_VALIDATION.json`
  - `reports/POST_STROKE_MIAMI_001_RUNTIME_OUTPUT.json`

## POST_STROKE_MIAMI_001 Runtime Snapshot
- Normalized profile includes explicit needs:
  - 24/7 nursing availability
  - rehabilitation capability
  - medication management
  - mobility limitations
- Requirement layers emitted at runtime:
  - MUST / OUR_RECOMMENDATION / NICE_TO_HAVE
- Candidate stage counts (runtime):
  - DISCOVERED: 100
  - IDENTITY_RESOLVED: 100
  - EVIDENCE_EVALUATED: 100
  - MUST_ELIGIBLE: 0
  - MUST_VERIFICATION_REQUIRED: 92
  - MUST_REJECTED: 8
  - RANKED: 92
  - TOP5_SELECTED: 5
- Top-5 output includes per-item governed package:
  - MUST satisfied/failed/unknown
  - verification-required evidence gaps
  - source traceability
  - ranking explanation

## Validation Notes
- `npm run lint` in frontend reports a pre-existing unrelated lint error in `frontend/src/app/page.tsx` (`react-hooks/set-state-in-effect`), outside this integration path.
- `pytest` not executed because `pytest` is not installed in current `.venv` (`No module named pytest`).
- Language-service error scan for changed files reports no file-level errors.

## Conclusion
- Governed architecture is now connected to the actual production runtime flow without creating a parallel recommendation engine.
- Runtime validator and case execution provide executable proof of integration behavior and anti-bypass constraints.
- External professional validation and benchmark status remain explicitly unchanged by design.
