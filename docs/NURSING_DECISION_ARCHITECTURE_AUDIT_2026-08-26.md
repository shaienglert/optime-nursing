# Nursing Decision Architecture Audit — 2026-08-26

## Executive finding

The current production path is functionally integrated but architecturally layered through multiple independent interpretation/orchestration stages. This allows the same client fact or facility fact to be re-derived after it was already governed, which explains repeated contradictions and makes latency difficult to control.

## Current production decision path

Observed layers on `main` before V2 migration:

1. `semantic_intent_ai.py`
   - AI statement accounting / clarification
   - raw questionnaire + free text

2. `patient_decision_engine.py`
   - legacy needs mapping
   - includes direct keyword/natural-language parsing and requirement weighting

3. `living_strategy_runtime.py`
   - independently parses raw questionnaire/free text again
   - independently derives household, ADL, medication, memory, rehab, social signals and strategies

4. `patient_decision_engine_runtime/__init__.py`
   - runs the governed engine with a very large internal limit
   - attaches human intelligence, strategy, provider evidence, agent evidence, client intent and ranking metadata

5. `services/__init__.py` import-hook wrapper
   - monkey-patches the public decision engine at import time
   - performs another profile/readiness pass
   - semantic facility requirements
   - combined-care layer
   - MUST→AI→NICE pipeline
   - AI Process Owner
   - recommendation suppression

6. `must_ai_nice_pipeline.py`
   - re-partitions candidate MUST state from `client_intent_fit`
   - invokes AI candidate ranking
   - invokes a separate AI NICE verification pass

7. `ai_candidate_ranking_runtime.py`
   - may sample governed claims for large candidate sets
   - sampled evidence is not guaranteed to include evidence already used by the authoritative MUST gate

8. `ai_process_owner_runtime.py`
   - receives a reduced downstream packet after prior engines have already made strategy, eligibility and ranking decisions
   - therefore currently acts more as a synthesis/next-action agent than the actual owner of the complete process

## Material architectural defects

### A1 — Raw client evidence is interpreted more than once

`semantic_intent_ai`, legacy `patient_decision_engine`, `living_strategy_runtime`, combined-care requirements and other helpers can each inspect questionnaire/free text independently.

Consequence: one client statement can produce different meanings in different layers.

Required V2 fix: raw client input is interpreted once into `CanonicalClientDecisionState`; downstream raw parsing is forbidden.

### A2 — Process Owner is downstream, not truly end-to-end

The Process Owner is attached after strategy, MUST, ranking and NICE machinery has already run.

Consequence: it cannot prevent earlier architectural mistakes; it can only react to them.

Required V2 fix: Semantic AI Process Owner produces the canonical client state and strategy before facility selection begins, then resumes ownership for comparison/recommendation/follow-up.

### A3 — More than one MUST representation exists

Legacy need levels, client-intent MUST buckets, combined-care reconciliation and downstream packets coexist.

Consequence: a capability can be PASS in one layer and UNKNOWN in another.

Required V2 fix: exactly one `AuthoritativeMustSnapshot` per facility per request.

### A4 — Evidence sampling can contradict authoritative state

AI candidate ranking may receive a distributed sample of claims while MUST evaluated the complete candidate record.

Observed production symptom: `MEDICATION_SUPPORT_AVAILABLE` in `mustPass` while AI ranking explanation reported medication support as UNKNOWN.

Required V2 fix: every ranking packet always includes the immutable authoritative MUST snapshot independently of any sampled/compacted evidence.

### A5 — Import-time monkey-patching obscures the execution path

`services/__init__.py` changes the decision-engine implementation through a meta-path finder and wraps it again.

Consequence: the effective production flow is difficult to reason about, test in isolation, profile and change safely.

Required V2 fix: one explicit `decision_orchestrator_v2.run(...)` entrypoint; no import-hook decision composition.

### A6 — Performance cost is architectural

A recommendation can trigger semantic client interpretation, large-universe candidate evaluation, multiple AI ranking batches, Top-N preference verification and Process Owner synthesis. The web backend is also on a sleeping Free Render instance.

Observed Mother-90 production duration after recent changes: ~285 seconds.

Required V2 fix:
- always-on production web service;
- precomputed compact canonical facility evidence packets;
- AI-scoring of every MUST-eligible candidate under one comparable rubric without re-sending raw evidence;
- only Top-N gets deep preference verification;
- cache stable facility semantic evidence between requests.

### A7 — Golden tests can encode the wrong product requirement

Observed smoke asserted exactly five visible candidates. Product requirement is up to five genuine fully eligible candidates.

Required V2 fix: Golden Cases assert decision quality and truthfulness, not arbitrary list length.

## Migration sequence

### Phase 1 — Foundation
- V2 architecture contract
- `CanonicalClientDecisionState`
- `CanonicalFacilityEvidenceState`
- authoritative MUST invariants
- canonical AI client interpretation contract

### Phase 2 — Move ownership upstream
- canonical AI output owns client requirements and strategy
- stop `living_strategy_runtime` and legacy natural-language mapper from making decisions in V2 path
- client clarification comes only from canonical Process Owner state

### Phase 3 — One explicit orchestrator
- add `decision_orchestrator_v2`
- explicit sequence; no import hook
- keep legacy engine only as temporary candidate-universe/evidence adapter where necessary

### Phase 4 — One facility truth
- Semantic Evidence Interpreter writes canonical capability/service-level state
- MUST reads canonical facility state only
- ranking/NICE/explanation read the same state

### Phase 5 — Rank all eligible efficiently
- compact persistent facility evidence packet
- globally comparable AI score for every MUST-eligible candidate
- final Top-N AI adjudication
- no candidate removed before AI scoring for performance convenience

### Phase 6 — Golden challenger audit
For Mother-90 and other Golden Cases, compare OPTIME against external AI challengers facility-by-facility:
- present in canonical universe?
- MUST PASS/PENDING/FAIL and evidence?
- NICE MATCH/MISMATCH/UNKNOWN?
- final rank?
- exact exclusion reason?

## Definition of done

V2 does not ship because CI is green. It ships only when:
- there is one explicit orchestration entrypoint;
- no downstream raw client re-parsing exists in the V2 path;
- every material fact has one authoritative state and provenance;
- contradictory downstream AI output fails closed;
- all MUST-eligible facilities participate in AI scoring/ranking;
- 1-5 final results are truthful and explainable;
- Golden Cases beat or at minimum defensibly match challenger decisions;
- warm production latency meets the V2 SLO.
