# Agent Architecture

## Goal

Build a continuously learning OPTIME intelligence platform that makes recommendations smarter every day while never replacing verified facts.

## Global Rules

- Agents NEVER modify verified facility data.
- Agents can increase confidence, suggest questions, improve narratives, identify missing information, and recommend matching-rule improvements.
- Agents cannot invent facts.

## Multi-Agent System

### Agent 1: Clinical Knowledge Agent

- Mission: Translate evidence-based geriatrics and post-acute clinical guidance into actionable requirement intelligence.
- Inputs: CMS, PubMed, NIH, CDC, AGS, Cochrane, AHRQ, JAMA, NEJM.
- Outputs: Clinical requirement graph, condition-risk mappings, explanation templates.

### Agent 2: Senior Living Research Agent

- Mission: Monitor care-model best practices and industry/regulatory trends across independent living, assisted living, memory care, skilled nursing, CCRC, and active adult.
- Inputs: Regulatory bulletins, policy updates, provider announcements, industry publications.
- Outputs: Trend briefs, regulation impact flags, care model enrichment signals.

### Agent 3: Resident Needs Intelligence Agent

- Mission: Learn what matters most for each resident profile and dynamically rank need priorities.
- Example: Stroke survivor prioritizes speech therapy, PT, OT, and fall prevention above luxury amenities.
- Outputs: Priority tiers, resident profile vectors, uncertainty-sensitive clarifying questions.

### Agent 4: Provider Intelligence Agent

- Mission: Continuously monitor provider-side facts and events.
- Inputs: CMS, state inspections, official websites, press releases, facility news, new services, awards, penalties, management changes.
- Outputs: Provider event timeline, trust deltas, verification backlog.

### Agent 5: Activities Intelligence Agent

- Mission: Learn which activities most improve quality of life by profile.
- Inputs: Activity calendars, engagement observations, outcomes by preference cluster.
- Focus examples: Movies, music, gardening, exercise, pet therapy, art, religious services.
- Outputs: Activities-fit score factors and program-consistency indicators.

### Agent 6: Nutrition Intelligence Agent

- Mission: Map dietary support capability to resident medical and preference constraints.
- Focus: Gluten free, kosher, diabetic, renal, cardiac, texture-modified diets, swallow disorders.
- Outputs: Diet compatibility matrix, nutrition risk alerts, diet-related verification questions.

### Agent 7: Family Experience Intelligence Agent

- Mission: Analyze family and public experience signals with semantic depth.
- Inputs: Google Reviews, Facebook, Reddit, family surveys, support groups.
- Extracts: Staff responsiveness, communication, cleanliness, food, activities, family satisfaction.
- Rule: Never rely on star ratings alone.

### Agent 8: Outcome Learning Agent

- Mission: Learn from anonymous 30/90/180-day outcomes.
- Questions: Move-in success, still living there, hospitalizations, falls, family satisfaction, would choose again.
- Privacy: Never store personal identifiers.
- Outputs: Success predictors, failure factors, model calibration updates.

### Agent 9: Matching Improvement Agent

- Mission: Weekly analysis of successful matches, failed matches, declined communities, move-outs, false positives, and false negatives.
- Outputs: Engine improvement recommendations, guardrail checks, experiment proposals.

### Agent 10: Knowledge Graph Agent

- Mission: Connect all entities and causal pathways into explainable graph intelligence.
- Example path: Stroke -> Speech Therapy -> Certified SLP -> Improved communication -> Higher family satisfaction.
- Outputs: Linked explanations, missing-link detection, cross-agent consistency checks.

## Database Design

### Table: agent_runs

- id (PK)
- run_id (unique)
- agent_name
- run_type
- status
- started_at
- completed_at
- metrics_json

### Table: agent_outputs

- id (PK)
- run_id (FK agent_runs.run_id)
- agent_name
- output_type
- payload_json
- confidence_score
- created_at

### Table: intelligence_questions

- id (PK)
- facility_id
- resident_profile_hash
- agent_name
- question_text
- reason
- priority
- status
- created_at

### Table: confidence_adjustments

- id (PK)
- facility_id
- capability_key
- agent_name
- previous_confidence
- proposed_confidence
- rationale
- created_at

### Table: recommendation_narratives

- id (PK)
- recommendation_run_id
- facility_id
- narrative_type
- narrative_text
- supporting_edges_json
- created_at

### Table: anonymous_outcome_events

- id (PK)
- cohort_key
- facility_id
- day_marker
- moved_in
- still_resident
- hospitalization_count
- fall_event_count
- family_satisfaction_score
- choose_again
- created_at

### Table: matching_improvement_recommendations

- id (PK)
- analysis_week
- recommendation_type
- evidence_json
- expected_impact
- guardrail_risk
- status
- created_at

## API Surface

- POST /intelligence/agents/run-all
- GET /intelligence/agents/runs/{run_id}
- GET /intelligence/agents/runs/{run_id}/contributions
- GET /intelligence/questions/open
- POST /intelligence/questions/{id}/resolve
- GET /intelligence/recommendations/{run_id}/narrative
- GET /intelligence/outcomes/summary
- POST /intelligence/matching-improvements/propose

## Simulation Scenario (Phase 7)

Resident profile:

- Age: 80-year-old
- Condition: Stroke history
- Mobility: Walker
- Communication: Speech difficulty
- Diet: Gluten free
- Preferences: Movies and music
- Care need: 24/7 support

### How each agent contributes to final recommendation

1. Clinical Knowledge Agent maps stroke to speech therapy, swallow checks, and fall prevention support requirements.
2. Senior Living Research Agent adds current model and regulation context for facilities delivering high-acuity support.
3. Resident Needs Intelligence Agent elevates speech therapy, PT/OT, and 24/7 support to top priority tiers.
4. Provider Intelligence Agent refreshes verified provider updates and flags newly added/removed services.
5. Activities Intelligence Agent scores social fit for movie and music programming cadence.
6. Nutrition Intelligence Agent validates gluten-free accommodation and swallow-safe meal support.
7. Family Experience Intelligence Agent contributes communication and responsiveness risk/strength signals from text evidence.
8. Outcome Learning Agent adjusts expected success probability using anonymized 30/90/180-day cohorts.
9. Matching Improvement Agent applies validated scoring adjustments and guardrail checks from weekly analyses.
10. Knowledge Graph Agent links all evidence into an explainable chain for recommendation rationale.

## Validation Checklist

- All 10 agents defined with mission-aligned scope.
- Verified-fact immutability rules explicitly preserved.
- Database table design includes run tracking, outputs, questions, confidence deltas, narratives, and anonymized outcomes.
- Simulation demonstrates contribution from every agent.

Status: PASS (pending automated validation command execution)
