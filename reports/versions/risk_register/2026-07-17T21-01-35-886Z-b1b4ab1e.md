# Risk Register

## Risk Matrix

| ID | Category | Risk | Likelihood | Impact | Current Controls | Gap | Mitigation Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Architecture | Client-side scoring drift from backend data state | Medium | High | Simulation regressions | No single backend scoring authority | High |
| R2 | Clinical | Narrative statements not always runtime-bound to persisted evidence links | Medium | High | Script validation | Missing runtime enforcement | High |
| R3 | Security | Provider identity and verification APIs need stronger abuse protection | Medium | High | Role checks and OTP flow | No visible rate-limit/anomaly layer | High |
| R4 | Privacy | OSINT data retention and deletion governance incomplete | Medium | High | Trusted-source policy | Missing operational controls and retention automation | High |
| R5 | Product | Provider adoption risk without full dashboard and lead tooling | High | High | API endpoints and simulations | Missing full portal UX | High |
| R6 | Performance | JSON-heavy profile table degrades queryability at scale | Medium | Medium | Indexed facility_id | Limited normalized child tables | Medium |
| R7 | Reliability | Verification and inbox workflow lacks queue and SLA orchestration | Medium | High | Request/response tables | Missing scheduler/escalation pipeline | High |
| R8 | Legal | Public-signal interpretation could create reputational exposure | Medium | Medium | Source provenance reporting | Missing legal review workflow flags | Medium |
| R9 | Business | Revenue capture delayed by absent subscription entitlements | High | Medium | Clear opportunity identified | Entitlement and billing domain absent | High |
| R10 | Data Quality | Outcome events partly synthetic in analysis workflows | Medium | Medium | Outcome scripts and benchmarks | Need stronger production telemetry ingestion | Medium |
| R11 | Scalability | Script-centric analytics creates operational bottlenecks | Medium | Medium | Extensive scripts | Missing service-level analytics endpoints | Medium |
| R12 | Compliance | Audit evidence fragmented across reports and logs | Medium | High | Audit tables and report outputs | Missing centralized compliance dashboard | High |

## Clinical Unsupported Statement Watchlist

Current codebase trend is improving, but guardrails are still needed for:

1. Overstating causal certainty in lifestyle-outcome relationships.
2. Presenting moderate or limited evidence as guaranteed benefit.
3. Using condition labels without family-language simplification.

## Mitigation Plan (Top 10)

1. Introduce backend scoring authority with immutable policy versioning.
2. Enforce recommendation-evidence linkage in runtime APIs.
3. Add API rate limiting, anti-automation controls, and abuse monitoring.
4. Launch provider inbox with SLA timers and escalation rules.
5. Build provider lead dashboard and CRM export integration.
6. Normalize intelligence signals and provenance into relational tables.
7. Add OSINT legal governance controls and retention lifecycle jobs.
8. Add de-identification audits for outcome-learning datasets.
9. Add compliance control dashboard (security, privacy, clinical guardrails).
10. Add continuous narrative QA checks for unsupported language.

## Risk Posture

Current risk posture is manageable for controlled rollout, but not yet optimized for large enterprise scale without the high-priority mitigations.
