from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.facility import Inspection
from app.services.cms_service import (
    CMS_INSPECTION_DATASET_ID,
    clean_state,
    download_dataset,
    iter_csv_rows,
)

_SERIOUS_CODES = {"G", "H", "I", "J", "K", "L"}


def import_inspection_data(db: Session, ccn_to_facility_id: dict, state: str = "FL") -> dict:
    file_path = download_dataset(CMS_INSPECTION_DATASET_ID, "inspection_citations.csv")

    db.query(Inspection).delete()
    db.commit()

    aggregate = defaultdict(lambda: {"deficiency_count": 0, "severe": 0, "infection": 0, "complaint": 0})
    failed_mappings = 0

    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue

        ccn = row.get("CMS Certification Number (CCN)")
        facility_id = ccn_to_facility_id.get(ccn or "")
        if not facility_id:
            failed_mappings += 1
            continue

        survey_date = row.get("Survey Date") or "Unknown"
        key = (facility_id, survey_date)

        aggregate[key]["deficiency_count"] += 1
        severity = (row.get("Scope Severity Code") or "").strip().upper()
        if severity and severity[0] in _SERIOUS_CODES:
            aggregate[key]["severe"] += 1
        if (row.get("Infection Control Inspection Deficiency") or "").strip().upper() == "Y":
            aggregate[key]["infection"] += 1
        if (row.get("Complaint Deficiency") or "").strip().upper() == "Y":
            aggregate[key]["complaint"] += 1

    for (facility_id, survey_date), values in aggregate.items():
        db.add(
            Inspection(
                facility_id=facility_id,
                inspection_date=survey_date,
                inspection_rating=None,
                deficiency_count=values["deficiency_count"],
                severe_deficiency_count=values["severe"],
                fine_amount=None,
                payment_denials_count=values["complaint"],
            )
        )

    db.commit()

    return {
        "inspection_rows_imported": len(aggregate),
        "missing_records": 0,
        "failed_mappings": failed_mappings,
    }
