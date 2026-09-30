"""Add explicit service fixtures to the existing catalog without changing prices or IDs."""
import base64
import gzip
import json
from pathlib import Path
from build_synthetic_pilot_facilities import pilot_service_evidence

path = Path(__file__).resolve().parents[1] / "database/synthetic_pilot/facility_universe.json.gz.b64"
data = json.loads(gzip.decompress(base64.b64decode(path.read_bytes())))
for row in data["records"]:
    index = int(row["canonical_id"].rsplit("-", 1)[1])
    row["pilot_service_evidence"] = pilot_service_evidence(index, row["synthetic_archetype"])
encoded = base64.b64encode(gzip.compress(json.dumps(data, indent=2).encode(), mtime=0)).decode()
path.write_text(encoded + "\n")
print(f"Updated {len(data['records'])} fictional service fixtures; prices and identities preserved")
