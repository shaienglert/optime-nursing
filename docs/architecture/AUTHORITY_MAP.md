# OOmnik Authority Map

This file is a guardrail against duplicate decision layers. Each concern has exactly one owner.

| Concern | Sole authority | AI role |
|---|---|---|
| Conversation experience | Conversational AI | Owns wording, explanation, reflection, tone |
| Which client fact is needed next | Canonical deterministic gap policy | Phrases the selected question only |
| Natural-language understanding | Structured Profile interpreter | Extracts to schema with quote/provenance |
| Conflict / unclear / out-of-schema | Structured Profile contract + deterministic policy | Explains and asks the governed clarification |
| Confirmed client truth | Versioned confirmed Structured Profile | Summarizes for confirmation |
| Facility truth | Versioned Facility Evidence Profile | Evidence AI may extract source facts only |
| Facility research refresh | Research Institute scheduler/event refresh | Evidence AI may extract; cannot rank |
| MUST eligibility | Deterministic Decision Engine | None |
| Budget/location/care rules | Deterministic Decision Engine | Explains returned result |
| NICE scoring/ranking | Deterministic Decision Engine | None; no AI tiebreak authority |
| True ties | Deterministic Decision Engine | Explains tie and offers Oomniker |
| Availability | Direct current facility verification; snapshot is informational | Explains verification status |
| License | Regulatory evidence authority | May extract document fields, not verify legally |
| Result presentation | Decision output order | AI explains only returned order |
| Parameter optimization | Oomniker analysis over confirmed profile + candidate snapshot | Recommends changes; user alone applies them |

## Forbidden duplicate authorities

- Frontend may not independently re-rank or re-decide eligibility.
- Semantic AI may not promote a preference to MUST.
- Candidate-ranking AI may not reorder deterministic results.
- Family search may not start public-web research that changes the active search snapshot.
- Research evidence may not overwrite provider facts silently.
- Raw family narrative may not enter Decision Engine after Structured Profile cutover.
- Availability snapshot may not become final availability in either direction.
