# INTELENGENTS AGENT: OPTIME Intelligence Collection Agent V1

Mission:
Continuously collect, normalize, deduplicate, analyze, and score publicly available intelligence signals for each facility in OPTIME.

Scope:
Only publicly available information is used.

Implemented Sources (current):
- Regulatory signals from existing CMS and inspection/staffing ingested data.
- Public review signals from stored review sources.
- Social presence proxy signals from public facility metadata.

Planned Source Connectors (public-only):
- Legal: public court records, lawsuits, settlements, enforcement actions.
- News: local news and public press releases.
- Social: official public social channels and event calendars.
- Employee: Indeed, Glassdoor, LinkedIn, public job postings.

Extracted Indices:
- Social Energy Index
- Family Satisfaction Index
- Staff Stability Index
- Regulatory Risk Index
- Litigation Risk Index
- Cultural Match Signals
- Activity Density Index
- Community Engagement Index
- Clinical Quality Index
- Reputation Index

Facility Intelligence Profile Contract:
- facility_id
- last_updated
- sources_used
- clinical_score
- family_score
- employee_score
- social_score
- reputation_score
- legal_risk_score
- regulatory_risk_score
- intelligence_confidence
- positive_signals[]
- negative_signals[]
- unresolved_risks[]
- intelligence_summary

Update Frequency Policy:
- News: Daily
- Social media: Daily
- Reviews: Daily
- Employee sources: Weekly
- Legal sources: Weekly
- Regulatory sources: Monthly

API:
- POST /intelligence/run
- POST /intelligence/run?facility_id={id}
- GET /intelligence/facilities/{id}
- GET /intelligence/schedule
