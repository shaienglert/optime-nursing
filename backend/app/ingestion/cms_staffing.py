from sqlalchemy.orm import Session

from app.models.facility import Staffing
from app.services.cms_service import (
    CMS_PROVIDER_DATASET_ID,
    clean_state,
    download_dataset,
    iter_csv_rows,
    to_float,
    to_int,
)

SOURCE_NAME = "CMS Provider Information (Staffing Fields)"


def import_staffing(db: Session, ccn_to_facility_id: dict, state: str = "FL") -> None:
    file_path = download_dataset(CMS_PROVIDER_DATASET_ID, "provider_information.csv")

    db.query(Staffing).delete()
    db.commit()

    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue

        ccn = row.get("CMS Certification Number (CCN)") or ""
        facility_id = ccn_to_facility_id.get(ccn)
        if not facility_id:
            continue

        db.add(
            Staffing(
                facility_id=facility_id,
                period_label="Provider Snapshot",
                staffing_rating=to_int(row.get("Staffing Rating")),
                rn_hours_per_resident_day=to_float(row.get("Reported RN Staffing Hours per Resident per Day")),
                total_nurse_hours_per_resident_day=to_float(row.get("Reported Total Nurse Staffing Hours per Resident per Day")),
                weekend_total_nurse_hours_per_resident_day=to_float(
                    row.get("Total number of nurse staff hours per resident per day on the weekend")
                ),
                source_name=SOURCE_NAME,
                source_date=row.get("Processing Date"),
                confidence_level="high",
            )
        )

    db.commit()
