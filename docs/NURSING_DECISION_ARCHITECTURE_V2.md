# OPTIME Nursing Decision Architecture V2

## Outcome

One AI-owned decision process from client intake to recommendation and follow-up, constrained by deterministic rules/Guardian. The system must never re-interpret an already-governed fact in a downstream layer.

## Single source of truth

There are exactly two authoritative state objects:

1. `CanonicalClientDecisionState`
   - normalized client facts
   - statement provenance
   - known / unknown / conflict state
   - MUST requirements
   - NICE preferences
   - living strategy candidates
   - unresolved client questions

2. `CanonicalFacilityEvidenceState`
   - canonical facility identity
   - normalized capabilities
   - service levels
   - source provenance
   - known / unknown / conflict state
   - freshness / confidence

Every downstream component reads these states. No downstream component may parse questionnaire text or natural-language input again to derive client facts, MUSTs, preferences, household state, or strategy.

## Ownership

### Semantic AI Process Owner

Owns the process sequence:

`UNDERSTAND -> CLARIFY -> STRATEGY -> RESEARCH -> COMPARE -> RECOMMEND -> VERIFY -> FOLLOW_UP`

Responsibilities:
- interpret arbitrary client language into canonical client facts;
- identify material ambiguity or contradiction;
- choose the next client question when client-owned information is missing;
- derive candidate living strategies from the canonical client state;
- rank only candidates that have passed deterministic MUST eligibility;
- explain trade-offs and propose complete solutions;
- request provider research when provider-owned facts are missing.

The Process Owner may not invent facility facts, override a MUST gate, or change a governed fact.

### Guardian / deterministic rules

Responsibilities:
- validate canonical state schemas and provenance;
- enforce MUST eligibility;
- enforce evidence service-level sufficiency;
- keep UNKNOWN as UNKNOWN;
- reject unsupported semantic interpretations;
- detect contradictions between authoritative state and downstream output;
- fail closed when required AI stages fail.

Guardian constrains and blocks. It does not own interview sequencing or ranking.

## Required pipeline

1. **Ingest client evidence once**
   - questionnaire answers
   - free text
   - prior adaptive answers / process continuity

2. **Semantic interpretation once**
   - produce `CanonicalClientDecisionState`
   - 100% statement accounting
   - preserve original statement and provenance

3. **Conflict resolution**
   - same-client contradictions -> ask client only if material
   - evidence-source contradictions -> source hierarchy / freshness; unresolved stays CONFLICT
   - derived-state contradiction -> system invariant failure; do not ask client

4. **Living strategy**
   - Process Owner derives strategies from canonical client state
   - no keyword parsing in strategy layer
   - deterministic Guardian validates safety/eligibility boundaries

5. **Candidate universe**
   - use complete canonical market universe for relevant strategy classes
   - no AI candidate invention

6. **MUST gate**
   - deterministic over all relevant candidates
   - PASS / PENDING_VERIFICATION / FAIL
   - PENDING is never shown as a recommendation

7. **Research queue**
   - research material MUST unknowns first
   - Semantic Evidence Interpreter maps arbitrary source wording to canonical capabilities
   - Guardian validates service level and provenance
   - write results back to `CanonicalFacilityEvidenceState`

8. **Shortlist before expensive AI ranking**
   - deterministic evidence-completeness / regulatory / strategy-fit shortlist of MUST-eligible candidates
   - target 20-30 candidates, not hundreds
   - shortlist cannot remove a candidate due only to an UNKNOWN NICE preference

9. **AI ranking**
   - one resident-specific ranking over the shortlist
   - consumes authoritative MUST snapshot and canonical evidence
   - MUST facts are immutable in the ranking packet
   - AI may rank and explain, never re-decide eligibility

10. **NICE verification**
    - verify only Top 5-10 against governed evidence
    - MATCH / MISMATCH requires evidence; UNKNOWN stays UNKNOWN
    - parallel/batched execution

11. **Recommendation**
    - show 1-5 genuine top candidates; never fabricate a fifth
    - distinguish verified fit from facts that still require provider confirmation
    - if required AI ranking fails, no user-visible fallback recommendation

12. **Follow-up / learning**
    - preserve canonical client state and comparison history
    - new evidence mutates only the relevant canonical fact with provenance
    - rerank from the same state; do not restart discovery

## Architectural invariants

1. `ONE_CLIENT_INTERPRETATION`: natural-language/questionnaire parsing occurs once before canonical client state is sealed for the run.
2. `ONE_MUST_GATE`: a MUST requirement has one authoritative status per facility.
3. `MUST_IMMUTABLE_DOWNSTREAM`: ranking/explanation cannot report a MUST as UNKNOWN if the authoritative gate says PASS, or PASS if it says UNKNOWN/FAIL.
4. `UNKNOWN_NEVER_DEFAULTS`: absence of evidence never becomes false, true, mismatch, or match by default.
5. `NO_DUPLICATE_STRATEGY_PARSING`: living strategy consumes canonical facts, not raw user text.
6. `NO_DUPLICATE_FACILITY_FACTS`: every facility capability is read from the canonical facility evidence state.
7. `NO_AI_CANDIDATE_INVENTION`: AI receives and returns only supplied canonical facility IDs.
8. `AI_FAILS_CLOSED_WHEN_REQUIRED`: required AI failure blocks recommendation visibility.
9. `SHORTLIST_BEFORE_AI`: AI ranking never scans the full market universe candidate-by-candidate.
10. `TOP_N_IS_UP_TO_FIVE`: fewer than five fully eligible candidates is a valid result.
11. `PROVENANCE_REQUIRED`: every PASS/MISMATCH on material facility capability is traceable to governed evidence.
12. `CONTRADICTION_BLOCKS_FINALITY`: unresolved material contradiction prevents FINAL.

## Performance SLO

Warm backend target for a normal recommendation request:
- canonical client interpretation: <= 8s
- deterministic universe + MUST gate: <= 2s
- material provider research: asynchronous or explicitly bounded
- shortlist AI ranking: <= 15s
- Top-N NICE verification + Process Owner synthesis: <= 10s
- target warm synchronous response: <= 35s

Production hosting must be always-on; cold-start delay is infrastructure and must not be hidden as AI latency.

## Golden acceptance tests

Every release must pass decision-level tests, not merely CI/build checks:

- Mother 90 / recent widow / Las Vegas / ADL + medication / social + classical music / $8k
- fully independent resident where Assisted Living must not outrank Independent Living merely due to richer data
- explicit Large Community preference vs Micro Home
- structured questionnaire vs semantically equivalent free text
- conflicting client statements requiring one targeted clarification
- provider evidence using non-catalog wording for a canonical capability
- material MUST unknown remains pending until researched
- required AI failure blocks recommendation

For each Golden Case, the audit must explain every benchmark/challenger facility: in universe? MUST pass/pending/fail? NICE evidence? final rank/exclusion reason?

## Migration rule

Do not add another patch layer around the current engine. V2 migration must remove or bypass duplicate interpretation/orchestration paths. Temporary adapters may translate legacy output into canonical state, but they may not make new decisions.