import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "database" / "professional_rule_registry.json"
REPORT_PATH = ROOT / "reports" / "PROFESSIONAL_RULE_GOVERNANCE_REPORT.md"
ENGINE_PATH = ROOT / "frontend" / "src" / "lib" / "optime-v2-engine.ts"
UNDERSTANDING_PATH = ROOT / "frontend" / "src" / "lib" / "understanding-profile.ts"


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_report_count(report_text: str, label: str):
    m = re.search(rf"-\s*{re.escape(label)}\s*:\s*(\d+)", report_text)
    if not m:
        return None
    return int(m.group(1))


def main() -> int:
    errors = []
    unknown_checks = []

    registry = _load_json(REGISTRY_PATH)
    rules = registry.get("rules", [])
    unknown_unmapped = registry.get("unknown_unmapped", [])
    weights = registry.get("hardcoded_weights_audit", [])

    # Inventory and identity checks
    missing_rule_id = [r for r in rules if not str(r.get("rule_id") or "").strip()]
    if missing_rule_id:
        errors.append(f"professional rule has no RULE_ID: {len(missing_rule_id)}")

    ids = [str(r.get("rule_id") or "").strip() for r in rules]
    duplicate_ids = sorted({rid for rid in ids if rid and ids.count(rid) > 1})
    if duplicate_ids:
        errors.append(f"duplicate/conflicting RULE_IDs exist: {', '.join(duplicate_ids)}")

    # MUST governance
    must_violations = []
    for rule in rules:
        output_classes = rule.get("allowed_output_class") or []
        if isinstance(output_classes, str):
            output_classes = [output_classes]
        if "MUST" not in output_classes:
            continue

        authority = str(rule.get("authority_level") or "").upper()
        source_type = str(rule.get("source_type") or "").upper()
        if authority != "A" and "USER_EXPLICIT" not in source_type:
            must_violations.append(str(rule.get("rule_id")))

    if must_violations:
        errors.append("MUST generated from unsupported level/source: " + ", ".join(must_violations))

    # Level D boundaries
    level_d_hard_exclusion = []
    level_d_our_reco = []
    for rule in rules:
        authority = str(rule.get("authority_level") or "").upper()
        if authority != "D":
            continue
        if bool(rule.get("hard_exclusion_allowed")):
            level_d_hard_exclusion.append(str(rule.get("rule_id")))

        output_classes = rule.get("allowed_output_class") or []
        if isinstance(output_classes, str):
            output_classes = [output_classes]
        if "OUR_RECOMMENDATION" in output_classes:
            level_d_our_reco.append(str(rule.get("rule_id")))

    if level_d_hard_exclusion:
        errors.append("Level D can hard-exclude: " + ", ".join(level_d_hard_exclusion))
    if level_d_our_reco:
        errors.append("Level D can independently generate OUR_RECOMMENDATION: " + ", ".join(level_d_our_reco))

    # Evidence traceability for active A/B
    missing_evidence_ab = []
    invalid_validator_ab = []
    invalid_validator_tokens = {
        "AI_AGENT",
        "INTERNAL_REVIEW_ONLY",
        "OPTIME_INTERNAL_ONLY",
        "INTERNAL_ONLY",
    }
    for rule in rules:
        if not rule.get("active_runtime"):
            continue
        authority = str(rule.get("authority_level") or "").upper()
        if authority not in {"A", "B"}:
            continue

        source_reference = str(rule.get("source_reference") or "").strip()
        if not source_reference:
            missing_evidence_ab.append(str(rule.get("rule_id")))

        validator_type = str(rule.get("validator_type") or "").strip().upper()
        if validator_type in invalid_validator_tokens:
            invalid_validator_ab.append(str(rule.get("rule_id")))

    if missing_evidence_ab:
        errors.append("active Level A/B rule lacks traceable evidence: " + ", ".join(missing_evidence_ab))
    if invalid_validator_ab:
        errors.append("AI/internal-only validator recorded as sole validator for Level A/B: " + ", ".join(invalid_validator_ab))

    # Unsupported hardcoded weight labeled validated
    invalid_weight_labels = []
    for weight in weights:
        classification = str(weight.get("classification") or "").upper()
        validation_status = str(weight.get("validation_status") or "").upper()
        if classification in {"UNVALIDATED", "UNKNOWN"} and "VALIDATED" in validation_status and validation_status != "UNVALIDATED":
            invalid_weight_labels.append(str(weight.get("weight_id")))

    if invalid_weight_labels:
        errors.append("unsupported hardcoded weight labeled validated: " + ", ".join(invalid_weight_labels))

    # UNKNOWN handling guard (mechanical check)
    engine_text = ENGINE_PATH.read_text(encoding="utf-8")
    understanding_text = UNDERSTANDING_PATH.read_text(encoding="utf-8")

    required_unknown_guard_snippets = [
        "UNKNOWN items excluded from match score",
        "unknown checklist item(s) reduce confidence only",
    ]
    for snippet in required_unknown_guard_snippets:
        if snippet not in engine_text:
            unknown_checks.append(f"missing required unknown guard snippet: {snippet}")

    suspicious_patterns = [
        r"assessment\.state\s*===\s*\"UNKNOWN\"\s*\?\s*0",
        r"UNKNOWN[^\n]{0,80}penalt",
        r"UNKNOWN[^\n]{0,80}hardRejection",
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, engine_text, flags=re.IGNORECASE):
            errors.append(f"UNKNOWN is silently converted into negative/zero pattern detected: {pattern}")

    # Report/registry count consistency
    if REPORT_PATH.exists():
        report_text = REPORT_PATH.read_text(encoding="utf-8")
        level_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for rule in rules:
            level = str(rule.get("authority_level") or "").upper()
            if level in level_counts:
                level_counts[level] += 1

        report_a = _extract_report_count(report_text, "LEVEL A")
        report_b = _extract_report_count(report_text, "LEVEL B")
        report_c = _extract_report_count(report_text, "LEVEL C")
        report_d = _extract_report_count(report_text, "LEVEL D")
        report_u = _extract_report_count(report_text, "UNKNOWN/UNMAPPED")

        if report_a is None or report_b is None or report_c is None or report_d is None or report_u is None:
            unknown_checks.append("report count markers missing for LEVEL A/B/C/D or UNKNOWN/UNMAPPED")
        else:
            if report_a != level_counts["A"]:
                errors.append(f"report/registry mismatch LEVEL A: report={report_a} registry={level_counts['A']}")
            if report_b != level_counts["B"]:
                errors.append(f"report/registry mismatch LEVEL B: report={report_b} registry={level_counts['B']}")
            if report_c != level_counts["C"]:
                errors.append(f"report/registry mismatch LEVEL C: report={report_c} registry={level_counts['C']}")
            if report_d != level_counts["D"]:
                errors.append(f"report/registry mismatch LEVEL D: report={report_d} registry={level_counts['D']}")
            if report_u != len(unknown_unmapped):
                errors.append(f"report/registry mismatch UNKNOWN/UNMAPPED: report={report_u} registry={len(unknown_unmapped)}")

    else:
        unknown_checks.append("governance report file not found for count cross-check")

    anti_hallucination_gate = "PASS" if not any("UNKNOWN is silently converted" in e for e in errors) and not unknown_checks else ("UNKNOWN" if unknown_checks else "FAIL")
    must_governance_gate = _status(not any("MUST generated" in e for e in errors))
    traceability_gate = _status(not any("traceable evidence" in e for e in errors))

    if errors:
        validation_state = "FAIL"
    elif unknown_checks:
        validation_state = "UNKNOWN"
    else:
        validation_state = "PASS"

    print(f"ANTI_HALLUCINATION_GATE={anti_hallucination_gate}")
    print(f"MUST_GOVERNANCE={must_governance_gate}")
    print(f"TRACEABILITY={traceability_gate}")
    print(f"VALIDATION={validation_state}")

    print(f"TOTAL_RULES={len(rules)}")
    level_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for rule in rules:
        level = str(rule.get("authority_level") or "").upper()
        if level in level_counts:
            level_counts[level] += 1
    print(f"LEVEL_A={level_counts['A']}")
    print(f"LEVEL_B={level_counts['B']}")
    print(f"LEVEL_C={level_counts['C']}")
    print(f"LEVEL_D={level_counts['D']}")
    print(f"UNKNOWN_UNMAPPED={len(unknown_unmapped)}")

    unvalidated_material_weights = [
        w for w in weights
        if bool(w.get("material_decision_impact")) and str(w.get("classification") or "").upper() in {"UNVALIDATED", "UNKNOWN"}
    ]
    print(f"UNVALIDATED_MATERIAL_WEIGHTS={len(unvalidated_material_weights)}")

    professional_validation_gaps = [
        r for r in rules
        if str(r.get("authority_level") or "").upper() in {"A", "B"}
        and str(r.get("validation_status") or "").upper() in {"EXTERNAL_VALIDATION_REQUIRED", "MECHANICAL_ONLY"}
    ]
    print(f"PROFESSIONAL_VALIDATION_GAPS={len(professional_validation_gaps)}")

    for err in errors:
        print(f"ERROR: {err}")
    for warn in unknown_checks:
        print(f"UNKNOWN_CHECK: {warn}")

    return 1 if validation_state == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
