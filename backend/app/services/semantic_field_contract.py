"""Declarative extraction contract shared by generation and acceptance.

This describes existing encodings and evidence requirements. Prompt examples
are not enum authority. Family fields cannot establish facility capabilities.
"""
from dataclasses import dataclass
import re
from typing import Union

from pydantic import StrictInt, StrictStr, TypeAdapter, ValidationError


@dataclass(frozen=True)
class FieldContract:
    kind: str = "Text"
    unit: str | None = None
    positive: bool = False
    dependency: tuple[str, str] | None = None
    owner: str = "FAMILY"

    @property
    def value_type(self):
        return {"Text": StrictStr, "List": list[StrictStr],
                "Selections": Union[StrictStr, list[StrictStr]],
                "Integer": StrictInt, "Months": Union[StrictStr, StrictInt]}[self.kind]

    def accepts_quote(self, quote):
        return self.unit is None or bool(re.search(UNIT_PATTERNS[self.unit], quote, re.IGNORECASE))

    def normalize(self, value, path):
        try:
            value = TypeAdapter(self.value_type).validate_python(value, strict=True)
        except ValidationError as exc:
            raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:INVALID_FIELD_VALUE:{path}") from exc
        if self.positive and value <= 0:
            raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:NONPOSITIVE_VALUE:{path}")
        if self.kind == "Selections" and isinstance(value, list):
            if not value:
                raise RuntimeError("SEMANTIC_AI_WIRE_CONTRACT:EMPTY_ASSISTANCE_SELECTIONS")
            return ", ".join(value)
        return str(value) if self.kind == "Months" and isinstance(value, int) else value


UNIT_PATTERNS = {
    "months": r"\bmonths?\b|חודש(?:ים|יים)?",
    "miles": r"\bmiles?\b|\bmi\b|מייל(?:ים)?",
}
FIELD_RULES = {
    "assistanceLevel": FieldContract(kind="Selections"),
    "budget": FieldContract(kind="Integer", positive=True),
    "maximumDistanceMiles": FieldContract(unit="miles"),
    "humanIntelligenceV2.transitionRiskProfile.temporarySupportMonths": FieldContract(kind="Months", unit="months"),
    "medicalCareProfile.dialysisFrequency": FieldContract(dependency=("medicalCareProfile.needs", "Dialysis")),
    "medicalCareProfile.dialysisCenter": FieldContract(dependency=("medicalCareProfile.needs", "Dialysis")),
    "medicalCareProfile.oxygenUse": FieldContract(dependency=("medicalCareProfile.needs", "Oxygen")),
    "medicalCareProfile.woundCareFrequency": FieldContract(dependency=("medicalCareProfile.needs", "Wound care")),
}


def canonical_source_path(path: str) -> str:
    """Normalize existing storage aliases, without interpreting their values."""
    return {"humanIntelligenceV2.socialProfile.hobbyParticipation": "happinessPreferences"}.get(path, path)


def leaves(obj, prefix=""):
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from leaves(value, path)
        else:
            yield path, value


def compile_fields(declarations):
    from app.services.canonical_structured_profile import in_schema
    fields = {}
    for path, declaration in leaves(declarations):
        if not in_schema(path):
            raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:UNAPPROVED_DECLARATION:{path}")
        fields[path] = FIELD_RULES.get(path, FieldContract(kind="List" if isinstance(declaration, list) else "Text"))
    return fields


def describe_fields(declarations):
    return {"source_owner": "FAMILY", "exact_source_quote_required": True,
            "fields": {path: {"representation": rule.kind,
                               **({"unit": rule.unit} if rule.unit else {}),
                               **({"positive": True} if rule.positive else {}),
                               **({"dependency": rule.dependency} if rule.dependency else {})}
                       for path, rule in compile_fields(declarations).items()}}


def profile_issues(profile, contracts):
    """Check only AI-established facts; preserve buttons and unknown states."""
    issues = []
    for path, field in profile["fields"].items():
        if field.get("provenance") != "AI_EXTRACTED":
            continue
        contract = contracts.get(path)
        if contract is None:
            issues.append(f"UNDECLARED_FIELD:{path}")
            continue
        if field.get("unverified_reason"):
            issues.append(f"NO_EXACT_FIELD_QUOTE:{path}")
        contract.normalize(field.get("value"), path)
        if field.get("state") != "EXPLICIT":
            continue
        if not contract.accepts_quote(str(field.get("quote") or "")):
            issues.append(f"UNSUPPORTED_UNIT:{path}:{contract.unit}")
        if contract.dependency and str(field.get("value")).strip().lower() not in {"not sure", "unknown", "none", "no"}:
            parent, expected = contract.dependency
            parent_field = profile["fields"].get(parent) or {}
            if parent_field.get("state") != "EXPLICIT" or expected not in (parent_field.get("value") or []):
                issues.append(f"UNSATISFIED_DEPENDENCY:{path}:{parent}:{expected}")
    return issues
