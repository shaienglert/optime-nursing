# OPTIME Master Roadmap

**Command ID:** OPTIME-005  
**Status:** IN_PROGRESS — dependency order established  
**Tracking issue:** #4

## Governing rules

1. One active objective at a time.
2. Dependencies before downstream experience work.
3. Extension before replacement.
4. No duplicate capability ownership.
5. No domain-specific implementation may be presented as universal infrastructure.
6. Every sprint requires code, test, runtime, and production evidence as applicable.
7. Owner approval is required to activate a new objective.
8. No capability may enter implementation unless it appears in this roadmap.

## Current active objective

`launch_nevada`

The active objective remains blocked at `source_intelligence`. The roadmap therefore does not jump directly to Universal Domain Engine work.

## Sprint sequence

### OPTIME-006 — Nevada Source Intelligence Closure

**Objective:** close the governed authoritative-source set required for Nevada launch.

**Capabilities:** `source_intelligence`

**Dependencies:** `constitution_governance`, `platform_registry`, source lifecycle registry, source policy engine.

**Exit criteria:**

- every discovered Nevada source has an explicit lifecycle state;
- mandatory versus optional sources are explicit;
- HCQC and NPPES have deterministic integrated/blocked dispositions;
- freshness and downstream-use policy exist;
- non-mocked runtime proof exists;
- Platform Registry recalculates the active objective;
- Market Builder is either unlocked or blocked by an exact remaining prerequisite.

### OPTIME-007 — Generic Market Builder

**Objective:** replace state-specific orchestration with one configuration-driven market build contract.

**Capabilities:** `market_builder`, `canonical_universe`

**Dependencies:** OPTIME-006 complete.

**Exit criteria:**

- one generic builder entry point;
- market config defines geography, source adapters, authority, identity keys, output paths, validation, and reports;
- Florida and Nevada run through the same orchestration contract;
- Texas can be onboarded through configuration plus source adapters, without new architecture;
- canonical artifacts and validation reports are deterministic.

### OPTIME-008 — Canonical Domain Intake Contract

**Objective:** define the governed input required to start a new OPTIME vertical.

**Capabilities:** `universal_domain_intake`

**Dependencies:** Platform Registry trusted; generic Market Builder contract established.

**Exit criteria:**

- canonical domain brief schema;
- decision target, user, provider, source, evidence, outcome, legal, market, and runtime requirements represented;
- owner approval boundary explicit;
- no Nursing-specific field is required by the universal core;
- validation rejects incomplete or contradictory briefs.

### OPTIME-009 — Objective and Capability Compiler

**Objective:** compile an approved domain brief into objectives, capabilities, dependencies, blockers, and acceptance contracts.

**Capabilities:** `objective_compiler`, `domain_capability_planner`, `dependency_planner`

**Dependencies:** OPTIME-008 complete.

**Exit criteria:**

- deterministic objective portfolio proposal;
- reuse/extend/new classification for every capability;
- dependency graph and current executable capability;
- no duplicate capability ownership;
- no automatic objective activation;
- owner approval required before execution.

### OPTIME-010 — Domain Source, Agent, and Validation Planners

**Objective:** compile the domain plan into governed source, workforce, validation, and learning plans.

**Capabilities:** `domain_source_planner`, `domain_agent_planner`, `domain_validation_planner`, `domain_learning_plan_compiler`

**Dependencies:** OPTIME-009 complete; Source Intelligence and agent workforce contracts reusable.

**Exit criteria:**

- authoritative-source discovery plan;
- agent reuse/new-agent proposal;
- evidence and validation plan;
- learning/outcome plan;
- explicit human/owner decisions;
- no agent or source becomes active without acceptance criteria.

### OPTIME-011 — Universal Execution Plan Compiler

**Objective:** convert the approved objective/capability/source/agent plan into a Supervisor-executable plan.

**Capabilities:** `domain_execution_plan_compiler`, `domain_runtime_provisioning_plan`

**Dependencies:** OPTIME-010 complete.

**Exit criteria:**

- bounded execution plan;
- retries, incidents, checkpoints, release gates, rollback, and runtime proof defined;
- Supervisor can execute only the active owner-approved objective;
- no architecture or constitutional change can be performed autonomously.

### OPTIME-012 — Cross-Domain Pilot

**Objective:** prove universality on one non-Nursing domain, preferably OPTIME Jobs because the owner has already defined its matching flow.

**Capabilities:** reuse full universal stack plus a domain configuration package.

**Dependencies:** OPTIME-011 complete.

**Exit criteria:**

- domain brief compiled without hand-authored platform architecture;
- source and market plan generated;
- agents and acceptance contracts generated;
- provider/candidate canonical universes built;
- decision and explanation flow works without Nursing-specific runtime assumptions;
- production pilot passes defined smoke tests.

## Work intentionally deferred

- broad Media expansion;
- cosmetic provider-portal work;
- new Nursing-specific knowledge agents;
- Universal Domain Engine implementation before OPTIME-006 and OPTIME-007 pass.

## Immediate next sprint

`OPTIME-006 — Nevada Source Intelligence Closure`

## Estimated remaining sprints to universal pilot

**7**, including the cross-domain pilot.

## Readiness gate

`READY_FOR_UNIVERSAL_DOMAIN_ENGINE: NO`

The gate becomes eligible for `YES` only after Source Intelligence closure and the Generic Market Builder are production-proven.