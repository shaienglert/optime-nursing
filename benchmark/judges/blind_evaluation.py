from __future__ import annotations

import random
from typing import Any


def build_blind_packet(run_records: list[dict[str, Any]], *, seed: int = 42) -> dict[str, Any]:
    shuffled = list(run_records)
    random.Random(seed).shuffle(shuffled)

    answers = []
    answer_keys = []
    for index, record in enumerate(shuffled):
        answer_id = f"ANSWER_{chr(ord('A') + index)}"
        answer_keys.append(
            {
                "answer_id": answer_id,
                "provider": record.get("provider"),
                "model": record.get("model"),
            }
        )

        answers.append(
            {
                "answer_id": answer_id,
                "case_id": record.get("case_id"),
                "track": record.get("track"),
                "normalized_response": record.get("normalized_response"),
                "metrics": record.get("metrics"),
                "provider": "REDACTED",
                "model": "REDACTED",
            }
        )

    return {
        "blind_packet": answers,
        "answer_key": answer_keys,
        "judge_instructions": {
            "no_identity_exposure": True,
            "required_outputs": ["dimension_score", "reason", "critical_error_flags"],
            "forbidden": ["self_grading_only", "provider_identity_inference_claims"],
        },
    }
