from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"pattern not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


main = Path("backend/app/main.py")
replace_once(
    main,
    '''class PatientDecisionEngineOut(BaseModel):\n    patient_needs_profile: Dict[str, Any]\n    results: List[Dict[str, Any]]\n    result_count: int\n    total_candidates_scored: int\n    availability_policy: str\n    care_setting_policy: Dict[str, Any] = Field(default_factory=dict)\n''',
    '''class PatientDecisionEngineOut(BaseModel):\n    patient_needs_profile: Dict[str, Any]\n    results: List[Dict[str, Any]]\n    result_count: int\n    total_candidates_scored: int\n    availability_policy: str\n    care_setting_policy: Dict[str, Any] = Field(default_factory=dict)\n    decision_intelligence: Dict[str, Any] = Field(default_factory=dict)\n    recommendation_audit_trace: Dict[str, Any] = Field(default_factory=dict)\n''',
)
replace_once(
    main,
    '''class PatientNeedsProfileOut(BaseModel):\n    generated_from: Dict[str, Any]\n    needs: List[Dict[str, Any]]\n    need_tags: List[str]\n    priority_parameter_ids: List[str]\n    profile_key: Optional[str] = None\n    location_city: Optional[str] = None\n    natural_language_mapping: Dict[str, Any]\n''',
    '''class PatientNeedsProfileOut(BaseModel):\n    generated_from: Dict[str, Any]\n    needs: List[Dict[str, Any]]\n    need_tags: List[str]\n    priority_parameter_ids: List[str]\n    profile_key: Optional[str] = None\n    location_city: Optional[str] = None\n    natural_language_mapping: Dict[str, Any]\n    decision_intelligence: Dict[str, Any] = Field(default_factory=dict)\n''',
)

api = Path("frontend/src/lib/api.ts")
replace_once(
    api,
    '''  natural_language_mapping: Record<string, unknown>;\n};\n\nexport type DecisionEngineRecommendation = {''',
    '''  natural_language_mapping: Record<string, unknown>;\n  decision_intelligence?: Record<string, unknown>;\n};\n\nexport type DecisionEngineRecommendation = {''',
)
replace_once(
    api,
    '''  comparison_parameter_ids: string[];\n};\n\nexport type DecisionEngineResponse = {''',
    '''  comparison_parameter_ids: string[];\n  human_person_fit?: Record<string, unknown>;\n  success_factor_trace?: Record<string, unknown>;\n};\n\nexport type DecisionEngineResponse = {''',
)
replace_once(
    api,
    '''  availability_policy: string;\n  tie_break_policy?: {''',
    '''  availability_policy: string;\n  decision_intelligence?: Record<string, unknown>;\n  recommendation_audit_trace?: Record<string, unknown>;\n  tie_break_policy?: {''',
)

Path("scripts/tmp_patch_decision_api_contract.py").unlink(missing_ok=True)
Path(".github/workflows/tmp-patch-decision-api-contract.yml").unlink(missing_ok=True)
