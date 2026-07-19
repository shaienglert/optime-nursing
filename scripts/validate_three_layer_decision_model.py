import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "database" / "three_layer_decision_model_schema.json"
REGISTRY_PATH = ROOT / "database" / "professional_rule_registry.json"
REPORT_PATH = ROOT / "reports" / "THREE_LAYER_DECISION_MODEL_REPORT.md"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors = []
    warnings = []

    schema = _load_json(SCHEMA_PATH)
    registry = _load_json(REGISTRY_PATH)

    required_classes = {"MUST", "OUR_RECOMMENDATION", "NICE_TO_HAVE", "CLARIFY", "INVESTIGATE", "UNKNOWN"}
    present_classes = set(schema.get("allowed_classifications", []))
    missing_classes = sorted(required_classes - present_classes)
    if missing_classes:
        errors.append("missing allowed classifications: " + ", ".join(missing_classes))

    boundaries = schema.get("governance_boundaries", {})
    must_origins = set(boundaries.get("must_allowed_origins", []))
    if must_origins != {"USER_EXPLICIT", "RULE_LEVEL_A"}:
        errors.append("must_allowed_origins must be exactly USER_EXPLICIT and RULE_LEVEL_A")

    level_d_restrictions = set(boundaries.get("level_d_restrictions", []))
    for token in ["NO_MUST", "NO_HARD_EXCLUSION", "NO_INDEPENDENT_OUR_RECOMMENDATION"]:
        if token not in level_d_restrictions:
            errors.append(f"missing Level D restriction: {token}")

    # Registry alignment checks for three-layer boundaries.
    rules = registry.get("rules", [])

    must_violations = []
    level_d_our_reco_violations = []
    level_d_hard_exclusion_violations = []

    for rule in rules:
        authority = str(rule.get("authority_level") or "").upper()
        source_type = str(rule.get("source_type") or "").upper()
        outputs = rule.get("allowed_output_class") or []
        if isinstance(outputs, str):
            outputs = [outputs]

        if "MUST" in outputs and not (authority == "A" or "USER_EXPLICIT" in source_type):
            must_violations.append(str(rule.get("rule_id")))

        if authority == "D" and "OUR_RECOMMENDATION" in outputs:
            level_d_our_reco_violations.append(str(rule.get("rule_id")))

        if authority == "D" and bool(rule.get("hard_exclusion_allowed")):
            level_d_hard_exclusion_violations.append(str(rule.get("rule_id")))

    if must_violations:
        errors.append("unsupported MUST origin(s): " + ", ".join(must_violations))
    if level_d_our_reco_violations:
        errors.append("Level D OUR_RECOMMENDATION violation(s): " + ", ".join(level_d_our_reco_violations))
    if level_d_hard_exclusion_violations:
        errors.append("Level D hard exclusion violation(s): " + ", ".join(level_d_hard_exclusion_violations))

    # Validation separation requirements.
    scenario_matrix = schema.get("scenario_validation_matrix", {})
    if scenario_matrix.get("synthetic_personas") != "REQUIRED_MECHANICAL":
        warnings.append("synthetic scenario status marker not set to REQUIRED_MECHANICAL")

    if not REPORT_PATH.exists():
        warnings.append("three-layer report not found")

    if errors:
        print("THREE_LAYER_VALIDATION=FAIL")
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("THREE_LAYER_VALIDATION=PASS")
    print(f"TOTAL_RULES_CHECKED={len(rules)}")
    print("MUST_GOVERNANCE=PASS")
    print("LEVEL_D_BOUNDARIES=PASS")
    if warnings:
        print("THREE_LAYER_WARNINGS=YES")
        for warning in warnings:
            print(f"WARNING: {warning}")
    else:
        print("THREE_LAYER_WARNINGS=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
