"""Add the coverage evidence (secured units, Medicaid acceptance) to the existing pilot
evidence fixture without changing prices, IDs or any other parameter. Idempotent."""
import base64
import gzip
import json
from pathlib import Path

from build_synthetic_pilot_facilities import coverage_evidence, evidence_record

ROOT = Path(__file__).resolve().parents[1] / "database/synthetic_pilot"
universe = json.loads(gzip.decompress(base64.b64decode((ROOT / "facility_universe.json.gz.b64").read_bytes())))
path = ROOT / "facility_parameter_evidence.json.gz.b64"
data = json.loads(gzip.decompress(base64.b64decode(path.read_bytes())))
covered = {"secured_units", "medicaid_attributes"}
records = [row for row in data["records"] if row["parameter_id"] not in covered]
stamp = data.get("generated_at_utc")
added = 0
for facility in universe["records"]:
    cid = facility["canonical_id"]
    index = int(cid.rsplit("-", 1)[1])
    for parameter_id, value in coverage_evidence(index, facility["synthetic_archetype"]).items():
        if value is not None:
            records.append(evidence_record(cid, facility["facility_name"], parameter_id, value, stamp))
            added += 1
data["records"] = records
data["record_count"] = len(records)
path.write_text(base64.b64encode(gzip.compress(json.dumps(data, indent=2).encode(), mtime=0)).decode() + "\n")
print(f"coverage records: {added}; total evidence records: {len(records)}")
