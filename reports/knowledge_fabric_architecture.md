# Knowledge Fabric Architecture

The Knowledge Fabric is the canonical structured layer between raw source processing and every downstream recommendation, explanation, provider profile, and platform surface.

| Layer | Role | Structured Output |
| --- | --- | --- |
| Ingestion | Transform raw source material into extracted facts and evidence traces. | Normalized fact candidates |
| Knowledge Object Model | Store reusable canonical facts with ownership, confidence, freshness, and history. | Knowledge Objects |
| Relationship Graph | Connect knowledge objects across entities, services, outcomes, evidence, and preferences. | Knowledge Relationships |
| Governance | Review, verify, retire, and audit knowledge quality. | Governance Records and History |
| Prepared Consumption | Expose structured packages to recommendations, narratives, provider pages, comparisons, and analytics. | Prepared Snapshots and Recommendation Packages |