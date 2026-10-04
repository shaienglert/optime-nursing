# Research → Product Decision Loop v1
Status: PROPOSED OPERATING PROTOCOL; not a deployed literature worker.
Owner: Shai Englert. Date: 2026-10-04.
## Principle impact
RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-005, PR-006, PR-007, PR-008, PR-009; knowledge improvement principles 7 and 10.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO for this research review and proposal registry (B: implementation completion). Specific future questionnaire, scoring and architecture changes require individual classification and a recorded owner decision. This document authorizes no production semantics.
## Workflow
1. Register source and provenance. A domain-only reference is UNRESOLVED, never “read”. Record title, DOI/PMID, publication/search dates, retrieval scope (full text/abstract/search excerpt), corrections/retractions and exact claim.
2. Produce a preliminary change proposal or an explicit NO_CHANGE conclusion. Detect whether it is already specified, already implemented, or genuinely new; no duplicate questions.
3. Review breadth BEFORE owner decision: outcome/PICO, queries/databases/date ranges, eligibility rules, records screened/included/excluded, countries, settings, cognition, methods, sample sizes, follow-up, uncertainty, risk of bias. Reviews may share primary studies: counts must not be added as independent corroboration.
4. Actively challenge each proposal: search null, harmful and contrary results, distinguish same-outcome contradictions from different-population results and evidence gaps. NO_CONTRADICTION_FOUND is not proof of consensus. Inaccessible texts and absent searches remain explicit blockers.
5. Prepare an owner decision card: current verified behavior (or NOT_VERIFIED), exact change, benefit, burden, evidence and counterevidence, affected schema/provider data, missing data, MUST safety, proposed evaluation, alternatives, confidence and recommended disposition.
6. Owner records APPROVE_EVALUATION / REQUEST_RESEARCH / REJECT / DEFER with date and rationale. Approval to evaluate is not approval to deploy.
7. Test approved change against a pinned baseline and representative personas, including memory care, couples, urgent hospital discharge and low budgets. Report changed questions, ranks/reasons, exclusions, unknown handling, burden and provider coverage. Every Oomniker relaxation must preserve MUST and count actual distinct added providers; offer only changes adding at least two suitable providers, as required by the product owner.
8. Owner records APPROVE_IMPLEMENTATION or another disposition against the exact evaluated proposal version.
9. Implement, verify in the live journey, record commit/deploy identifiers and rollback. Neither merged PR nor passing CI alone proves live behavior.
10. Monitor separately: resident adjustment, resident/family satisfaction, avoidable transfer, clinical outcomes, response burden. Review new evidence and reopen affected proposals; never learn policy automatically.
## Honest states and gates
SOURCE_PENDING → PRELIMINARY_PROPOSAL → EVIDENCE_REVIEW → READY_FOR_OWNER → EVALUATION_APPROVED → EVALUATED → IMPLEMENTATION_APPROVED → IMPLEMENTED → LIVE_VERIFIED → OUTCOME_REVIEW.
Any stage can become REQUEST_RESEARCH, REJECTED or DEFERRED; no skipped stages. Evidence conflicts reopen review.
READY_FOR_OWNER requires an adequate, documented review for the proposed use, current behavior verification, provider coverage and an evaluation plan. Implemented means a real code reference; live verified means observed production evidence.
## Delivery contract
Deliver a Hebrew card to the owner when a substantive proposal is ready, with a link to the evidence record. An incomplete review is delivered as preliminary with explicit blockers. Reports distinguish NEW_PROPOSAL / EXISTING_POLICY_IMPLEMENTATION_GAP / NO_CHANGE / INSUFFICIENT_EVIDENCE.
Do not equate scheduler runs, output counts or templated documents with research activity. Log real sources retrieved and claims assessed. Send email only under separately authorized delivery instructions.
## Operational acceptance (still pending)
A real literature-discovery worker must consume these records; the current run_daily_research job only refreshes facilities/regulation. Before declaring this loop active, show an actual new source → challenged recommendation → owner delivery → recorded decision → evaluation → deployment → live check. This PR provides the protocol and first review packet, not that runtime integration.
