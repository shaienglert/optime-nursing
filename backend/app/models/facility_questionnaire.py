"""Provider questionnaire aligned to resident intake; V1 exports stay compatible."""
import json
from pathlib import Path
from typing import Dict, List

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "database" / "facility_intake_alignment_v2.json"
FACILITY_ALIGNMENT = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
ANSWER_STATES: List[str] = FACILITY_ALIGNMENT["answer_states"]
FACILITY_QUESTIONNAIRE_V1: Dict[str, List[dict]] = FACILITY_ALIGNMENT["sections"]

def facility_questionnaire_v1_flat() -> List[dict]:
    return [{"section": section, **question}
            for section, questions in FACILITY_QUESTIONNAIRE_V1.items()
            for question in questions]

def consumer_question_ids(key: str) -> List[str]:
    return [qid for qid, row in FACILITY_ALIGNMENT["consumer_mapping"].items()
            if key in row["provider_keys"]]
