from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from app.services.facility_parameter_service import get_canonical_facility_index
from app.services.human_intelligence_runtime_verified import build_human_intelligence_context
from app.services.patient_decision_engine import run_patient_decision_engine


class Mother90ExternalCandidateDiagnosticTests(unittest.TestCase):
    def test_external_ai_candidates_positions_and_rank_dimensions(self) -> None:
        state = {
            "relationship": "Mom",
            "ageGroup": "90+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "budget": 8000,
            "distanceFromFamily": "Balanced location",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "No preference"},
                "familyProfile": {"socialInteractionNeed": "Important"},
                "transitionRiskProfile": {"attitudeTowardMove": "Cautious but open"},
                "scoringEngine": {"adaptiveSignals": []},
            },
        }
        query = (
            "My mother is 90 and we are looking across the Las Vegas Valley. She is mentally alert, "
            "has no dementia, is mobile, but needs daily help with bathing, dressing and medication. "
            "She would like a friendly social environment and we want the least restrictive safe setting."
        )
        ready_ai = {"decision_readiness": "READY", "next_question": None, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ready_ai
        ):
            result = run_patient_decision_engine(state, query, limit=500)

        aliases = {
            "Oakmont of Las Vegas": ["oakmont"],
            "Las Ventanas at Summerlin": ["las ventanas"],
            "Legacy House of Southern Hills": ["legacy house", "southern hills"],
            "Merrill Gardens at Green Valley Ranch": ["merrill gardens", "green valley ranch"],
            "Sunrise of Henderson": ["sunrise of henderson", "sunrise henderson"],
        }
        rows = result.get("results") or []
        canonical = get_canonical_facility_index()

        def compact(row):
            fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
            care = row.get("care_setting_fit") if isinstance(row.get("care_setting_fit"), dict) else {}
            history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}
            rep = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}
            return {
                "rank": row.get("rank_position"),
                "facility_name": row.get("facility_name"),
                "canonical_id": row.get("canonical_facility_id"),
                "canonical_type": row.get("canonical_type"),
                "housing_modalities": row.get("housing_modalities") or [],
                "city": row.get("city"),
                "hard_gate": fit.get("hard_gate"),
                "must_pass": fit.get("must_pass") or [],
                "must_unknown": fit.get("must_unknown") or [],
                "nice_match": fit.get("nice_match") or [],
                "nice_unknown": fit.get("nice_unknown") or [],
                "care_setting_fit": care.get("status"),
                "regulatory_grade": history.get("latest_known_grade"),
                "disciplinary_action": history.get("disciplinary_action"),
                "public_rating": rep.get("rating"),
                "public_review_count": rep.get("review_count"),
                "evidence_known": fit.get("relevant_evidence_known_count"),
                "evidence_unknown": fit.get("relevant_evidence_unknown_count"),
            }

        diagnostics = {
            "top10": [compact(r) for r in rows[:10]],
            "targets": {},
            "returned_count": len(rows),
            "total_candidates_scored": result.get("total_candidates_scored"),
        }
        for label, needles in aliases.items():
            found = [r for r in rows if any(n in str(r.get("facility_name") or "").lower() for n in needles)]
            if found:
                diagnostics["targets"][label] = [compact(r) for r in found]
                continue
            canon_matches = []
            for cid, crow in canonical.items():
                name = str(crow.get("facility_name") or crow.get("name") or "").lower()
                if any(n in name for n in needles):
                    canon_matches.append({
                        "canonical_id": cid,
                        "facility_name": crow.get("facility_name") or crow.get("name"),
                        "canonical_type": crow.get("canonical_type"),
                        "housing_modalities": crow.get("housing_modalities") or [],
                        "city": crow.get("city"),
                        "is_las_vegas_valley": crow.get("is_las_vegas_valley"),
                        "status": "IN_CANONICAL_BUT_NOT_IN_RETURNED_NON_REJECTED_RANKING",
                    })
            diagnostics["targets"][label] = canon_matches or [{"status": "NOT_FOUND_IN_CANONICAL_UNIVERSE"}]

        print("MOTHER90_EXTERNAL_CANDIDATES=" + json.dumps(diagnostics, indent=2, default=str))
        self.assertTrue(rows)


if __name__ == "__main__":
    unittest.main()
