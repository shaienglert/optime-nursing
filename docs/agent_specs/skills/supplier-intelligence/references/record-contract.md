# Supplier Record Contract

Each canonical record must support the following structure. Unknown fields remain null and appear in `unknown_fields`.

```json
{
  "supplier_id": "stable canonical id",
  "legal_name": "string or null",
  "brand_name": "string",
  "sector_ids": ["HOME_CARE"],
  "branch": {
    "address": "string or null",
    "phone": "string or null",
    "website": "https://...",
    "service_area": ["Las Vegas"],
    "las_vegas_valley_verified": true
  },
  "services": [],
  "payment_options": [],
  "licenses": [],
  "ratings": [],
  "facility_referrals": [],
  "oomnik_feedback": {
    "status": "NOT_YET_AVAILABLE",
    "verified_review_count": 0,
    "dimensions": {}
  },
  "involvement": "DIRECTORY",
  "critical_readiness": null,
  "commercial_relationship": {
    "status": "NONE_KNOWN",
    "disclosure": null
  },
  "evidence_refs": [],
  "unknown_fields": [],
  "conflicts": [],
  "freshness": {
    "last_verified_at": "ISO-8601 timestamp",
    "status": "FRESH"
  },
  "publication": {
    "status": "CANDIDATE",
    "reasons": []
  }
}
```

Each `ratings` item must contain `source`, `branch_identity`, `rating`, `review_count`, `observed_at`, and `source_url`. Preserve ratings separately; do not create a synthetic star average.

Each `licenses` item must contain `license_type`, `license_number`, `status`, `holder_name`, `expires_at`, `verified_at`, and `source_url` when applicable.

`critical_readiness` is required when `involvement` is `OUTCOME_CRITICAL`. It must record capacity confirmed, service scope, quoted price status, start date status, backup coverage, last confirmation, and unresolved blockers. Public ratings do not prove readiness.

## Publication states

- `CANDIDATE`: discovered but not ready for public display.
- `LIMITED`: identity and local service are established but important evidence is missing.
- `VERIFIED`: required identity, geography, licensing, and evidence gates pass.
- `SUSPENDED`: material license, safety, identity, or operational concern.
- `CLOSED`: confirmed no longer operating.

Never delete a prior state. Supersede it with a timestamped observation.

