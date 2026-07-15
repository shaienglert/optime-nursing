from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.facility import Inspection
from app.services.cms_service import (
    CMS_INSPECTION_DATASET_ID,
    clean_state,
    download_dataset,
    iter_csv_rows,
)

SOURCE_NAME = "CMS Health Deficiencies"
_SERIOUS_CODES = {"G", "H", "I", "J", "K", "L"}


def import_inspections(db: Session, ccn_to_facility_id: dict, state: str = "FL") -> None:
    file_path = download_dataset(CMS_INSPECTION_DATASET_ID, "inspection_citations.csv")

    db.query(Inspection).delete()
    db.commit()

    grouped = defaultdict(lambda: {"def": 0, "severe": 0, "complaints": 0, "infection": 0, "date": ""})

    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue

        ccn = row.get("CMS Certification Number (CCN)") or ""
        facility_id = ccn_to_facility_id.get(ccn)
        if not facility_id:
            continue

        survey_date = row.get("Survey Date") or "Unknown"
        key = (facility_id, survey_date)
        grouped[key]["date"] = survey_date
        grouped[key]["def"] += 1

        severity = (row.get("Scope Severity Code") or "").strip().upper()
        if severity and severity[0] in _SERIOUS_CODES:
            grouped[key]["severe"] += 1

        if (row.get("Complaint Deficiency") or "").strip().upper() == "Y":
            grouped[key]["complaints"] += 1

        if (row.get("Infection Control Inspection Deficiency") or "").strip().upper() == "Y":
            grouped[key]["infection"] += 1

    for (facility_id, _), agg in grouped.items():
        db.add(
            Inspection(
                facility_id=facility_id,
                inspection_date=agg["date"],
                inspection_rating=None,
                deficiency_count=agg["def"],
                severe_deficiency_count=agg["severe"],
                fine_amount=None,
                payment_denials_count=agg["complaints"],
                source_name=SOURCE_NAME,
                source_date=agg["date"],
                confidence_level="high",
            )
        )

    db.commit()
