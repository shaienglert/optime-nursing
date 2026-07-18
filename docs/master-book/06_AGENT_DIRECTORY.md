# 06 Agent Directory

## Purpose
Provide complete operational directory for every defined agent.

## Current Implementation
- Agent catalog and specs live in docs/agent_specs/.
- Operational status and tasks are reported in reports/*.md.

## Architecture
- Agents modeled as spec + queue + productivity + status surfaces.
- Agent telemetry persisted in agent_execution model tables.

## Dependencies
- docs/agent_specs/agent_catalog.md
- reports/agent_status_report.md
- reports/agent_task_queue.md
- reports/agent_productivity_dashboard.md

## Current Status
- Implemented with partial operational inconsistencies across some generated views.

## Completed Work
### Clinical Knowledge Agent
- Mission: Clinical Knowledge in domain Clinical care requirements.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Clinical care requirements
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Review new domain research and trusted guidelines. | Publish verified knowledge and evidence objects.
- Learning responsibilities: Knowledge growth; Evidence growth; Coverage; Confidence; Accuracy
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 10; evidencePerDay=>= 15; providerUpdatesPerDay=N/A; relationshipsPerDay=>= 8; coverageGrowthPerDay=>= 1%
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Provider Intelligence Agent
- Mission: Provider Repository in domain Provider verified capabilities.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Provider verified capabilities
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Discover new Florida communities and provider changes from trusted sources. | Detect ownership, licensing, and service-line changes.
- Learning responsibilities: Provider growth; Coverage; Duplicate rate; Verification success; Refresh success
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 12; evidencePerDay=>= 12; providerUpdatesPerDay=>= 20; relationshipsPerDay=>= 10; coverageGrowthPerDay=>= 1 county
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Clinical Evidence Agent
- Mission: Evidence Repository in domain Evidence repository.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Evidence repository
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: UNPROVEN
- Current tasks: Verify newly discovered entities and changed facts. | Resolve contradictions and track uncertainty explicitly.
- Learning responsibilities: Evidence growth; Coverage; Confidence; Duplicate rate; Refresh success
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 8; evidencePerDay=>= 20; providerUpdatesPerDay=N/A; relationshipsPerDay=>= 10; coverageGrowthPerDay=>= 1 topic cluster
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Activities Intelligence Agent
- Mission: Activities Knowledge in domain Activity and engagement fit.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Activity and engagement fit
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Review new domain research and trusted guidelines. | Publish verified knowledge and evidence objects.
- Learning responsibilities: Knowledge growth; Evidence growth; Coverage; Confidence; Refresh success
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 10; evidencePerDay=>= 10; providerUpdatesPerDay=>= 12; relationshipsPerDay=>= 8; coverageGrowthPerDay=>= 1 provider segment
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Nutrition Intelligence Agent
- Mission: Nutrition Knowledge in domain Dietary and nutrition support.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Dietary and nutrition support
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Review new domain research and trusted guidelines. | Publish verified knowledge and evidence objects.
- Learning responsibilities: Knowledge growth; Evidence growth; Coverage; Confidence; Refresh success
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 8; evidencePerDay=>= 8; providerUpdatesPerDay=>= 10; relationshipsPerDay=>= 6; coverageGrowthPerDay=>= 1 diet-support segment
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Outcome Learning Agent
- Mission: Outcome Learning in domain Outcome-based calibration.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Outcome-based calibration
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Verify newly discovered entities and changed facts. | Resolve contradictions and track uncertainty explicitly.
- Learning responsibilities: Knowledge growth; Evidence growth; Accuracy; Learning progress; Coverage
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 8; evidencePerDay=>= 8; providerUpdatesPerDay=N/A; relationshipsPerDay=>= 6; coverageGrowthPerDay=>= 1 cohort segment
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Knowledge Graph Agent
- Mission: Knowledge Graph in domain Cross-domain relationship graph.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Cross-domain relationship graph
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Link new knowledge objects into the knowledge graph. | Detect orphan objects and missing relationships.
- Learning responsibilities: Knowledge graph growth; Coverage; Confidence; Duplicate rate; Refresh success
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 8; evidencePerDay=>= 5; providerUpdatesPerDay=N/A; relationshipsPerDay=>= 12; coverageGrowthPerDay=>= 1 ontology cluster
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Data Quality & Trust Agent
- Mission: Data Quality in domain Freshness, consistency, and provenance.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Freshness, consistency, and provenance
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Discover new Florida communities and provider changes from trusted sources. | Detect ownership, licensing, and service-line changes.
- Learning responsibilities: Coverage; Confidence; Duplicate rate; Refresh success; Discovery success
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 6; evidencePerDay=>= 6; providerUpdatesPerDay=>= 10 quality reviews; relationshipsPerDay=>= 6; coverageGrowthPerDay=>= 1 quality segment
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Narrative Intelligence Agent
- Mission: Narrative Layer in domain Narrative intelligence.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Narrative intelligence
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: UNPROVEN
- Current tasks: Convert prepared institutional knowledge into advisor-ready guidance. | Improve explanation quality while preserving uncertainty.
- Learning responsibilities: Accuracy; Response time; Coverage; Confidence; Learning progress
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 4; evidencePerDay=>= 4 narrative references; providerUpdatesPerDay=N/A; relationshipsPerDay=>= 4; coverageGrowthPerDay=>= 1 explanation pattern
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Matching Improvement Agent
- Mission: Matching Policy in domain Deterministic ranking policy upgrades.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Deterministic ranking policy upgrades
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: ACTIVE
- Current tasks: Verify newly discovered entities and changed facts. | Resolve contradictions and track uncertainty explicitly.
- Learning responsibilities: Recommendation quality; Accuracy; Learning progress; Coverage; Confidence
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 6; evidencePerDay=>= 6; providerUpdatesPerDay=N/A; relationshipsPerDay=>= 5; coverageGrowthPerDay=>= 1 ranking issue family
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Competitive Intelligence Agent
- Mission: Competitive Intelligence in domain Competitive and market intelligence.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Competitive and market intelligence
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: UNPROVEN
- Current tasks: Discover new Florida communities and provider changes from trusted sources. | Detect ownership, licensing, and service-line changes.
- Learning responsibilities: Coverage growth; Discovery success; Learning progress; Response time; Confidence
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 5; evidencePerDay=>= 5; providerUpdatesPerDay=>= 3 prioritized discovery campaigns; relationshipsPerDay=>= 4; coverageGrowthPerDay=>= 1 geography priority update
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.

### Chief AI Supervisor
- Mission: Supervisory Governance in domain Supervisory governance.
- Responsibilities: see docs/agent_specs/*_spec.md and docs/agent_specs/agent_responsibility_matrix.md.
- Knowledge Domain: Supervisory governance
- Inputs: trusted sources listed in each agent spec input table.
- Outputs: knowledge objects, evidence objects, queue actions, and reports.
- Current implementation: Implemented (spec-driven).
- Current operational status: UNPROVEN
- Current tasks: Discover new Florida communities and provider changes from trusted sources. | Detect ownership, licensing, and service-line changes.
- Learning responsibilities: Agent health; Knowledge growth; Provider growth; Coverage growth; Evidence growth
- Dependencies: see docs/agent_specs/agent_interaction_matrix.md and docs/agent_specs/knowledge_ownership_matrix.md.
- KPIs: knowledgeObjectsPerDay=>= 1 readiness cycle; evidencePerDay=>= 1 validation bundle; providerUpdatesPerDay=>= 1 budget reprioritization when needed; relationshipsPerDay=>= 1 supervisory linkage set; coverageGrowthPerDay=>= maintain zero idle agents
- Reports: reports/agent_status_report.md, reports/agent_productivity_dashboard.md, reports/knowledge_gap_report.md.


## Remaining Work
- Align all generated agent surfaces to one canonical registry output.

## Known Limitations
- Some generated surfaces currently display UNPROVEN_AGENT placeholders.

## Next Implementation Steps
- Restore canonical naming map before producing executive scorecards.
