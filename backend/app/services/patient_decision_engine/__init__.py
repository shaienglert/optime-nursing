"""Public compatibility facade; one explicit production runtime.

No import interception, dynamic source loading or function replacement.
"""
from app.services.patient_decision_engine_runtime import (
    build_patient_needs_profile, build_patient_comparison_context, run_patient_decision_engine, _regulatory_index, _governed, _is_rankable_candidate,
)
from app.services.decision_engine_core import STRUCTURED_INTAKE_MAPPING_CONTRACT

__all__ = ["build_patient_needs_profile", "build_patient_comparison_context", "run_patient_decision_engine"]
