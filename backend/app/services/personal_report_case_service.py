from __future__ import annotations

"""Case persistence for the Personal Decision Report.

Kept separate from personal_decision_report_builder.py on purpose: the builder is a
pure, closed-world function (no DB, no IO) and must stay that way. This module is the
IO boundary -- it remembers a case's inputs so a client can request an updated report
in 24-72h without re-entering their questionnaire, and keeps a snapshot of every report
generated for a case for future before/after comparison.
"""

import json
from typing import Any, Mapping, Optional

from sqlalchemy.orm import Session

from app.models.personal_report_case import PersonalReportCase, PersonalReportSnapshot


def create_case(
    db: Session,
    *,
    questionnaire_state: Mapping[str, Any],
    natural_language_query: str,
    limit: int,
) -> PersonalReportCase:
    case = PersonalReportCase(
        questionnaire_state_json=json.dumps(dict(questionnaire_state)),
        natural_language_query=natural_language_query or "",
        limit=limit,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def get_case_by_token(db: Session, case_token: str) -> Optional[PersonalReportCase]:
    return db.query(PersonalReportCase).filter(PersonalReportCase.case_token == case_token).first()


def case_inputs(case: PersonalReportCase) -> dict[str, Any]:
    return {
        "questionnaire_state": json.loads(case.questionnaire_state_json),
        "natural_language_query": case.natural_language_query or "",
        "limit": case.limit,
    }


def save_snapshot(db: Session, *, case_id: int, report_ready: bool, report: Mapping[str, Any]) -> PersonalReportSnapshot:
    snapshot = PersonalReportSnapshot(
        case_id=case_id,
        report_ready=report_ready,
        report_json=json.dumps(dict(report)),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
