"""Owner-directed 2026-10-04 advisor changes; decision fields remain under exact parity."""
import re

_ROOTS = ("$.run_limit5.oomniker", "$.run_limit50.oomniker", "$.http_recommendations.body.oomniker")
_STORED = re.compile(r"^\$\.db_side_effects\.decision_artifacts\[\d+\]\.payload_json\.oomniker(?:[.\[]|$)")
_SOURCE_PATHS = re.compile(r"\.dynamic_preference_model\.preferences\[\d+\]\.mapped_parameters$")

def is_declared_advisory_change(path: str, kind: str) -> bool:
    # These are the deliberately changed advisor contract, not MUST eligibility,
    # family criteria, prices, facility evidence, scores or recommendation order.
    if any(path == root or path.startswith(root + ".") or path.startswith(root + "[") for root in _ROOTS):
        return True
    if _STORED.search(path):
        return True
    # Provenance is additive only; changed/removed source paths still fail.
    return kind == "added" and bool(_SOURCE_PATHS.search(path))
