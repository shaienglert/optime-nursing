from sqlalchemy.orm import Session

from app.models.facility import Facility, Staffing
from app.services.cms_service import (
    CMS_PROVIDER_DATASET_ID,
    clean_state,
    download_dataset,
    iter_csv_rows,
    to_float,
    to_int,
)


def import_staffing_data(db: Session, ccn_to_facility_id: dict, state: str = "FL") -> dict:
    file_path = download_dataset(CMS_PROVIDER_DATASET_ID, "provider_information.csv")

    db.query(Staffing).delete()
    db.commit()

    imported = 0
    missing_records = 0
    failed_mappings = 0

    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue

        ccn = row.get("CMS Certification Number (CCN)")
        facility_id = ccn_to_facility_id.get(ccn or "")
        if not facility_id:
            failed_mappings += 1
            continue

        rn_hours = to_float(row.get("Reported RN Staffing Hours per Resident per Day"))
        total_hours = to_float(row.get("Reported Total Nurse Staffing Hours per Resident per Day"))
        weekend_hours = to_float(row.get("Total number of nurse staff hours per resident per day on the weekend"))

        if rn_hours is None and total_hours is None:
            missing_records += 1

        db.add(
            Staffing(
                facility_id=facility_id,
                period_label="CMS Provider Info (PBJ-derived)",
                staffing_rating=to_int(row.get("Staffing Rating")),
                rn_hours_per_resident_day=rn_hours,
                total_nurse_hours_per_resident_day=total_hours,
                weekend_total_nurse_hours_per_resident_day=weekend_hours,
            )
        )
        imported += 1

    db.commit()

    # Keep Facility.staffing_rating in sync with latest provider row.
    facilities = db.query(Facility).all()
    for facility in facilities:
        latest = (
            db.query(Staffing)
            .filter(Staffing.facility_id == facility.id)
            .order_by(Staffing.id.desc())
            .first()
        )
        if latest and latest.staffing_rating is not None:
            facility.staffing_rating = latest.staffing_rating
    db.commit()

    return {
        "staffing_rows_imported": imported,
        "missing_records": missing_records,
        "failed_mappings": failed_mappings,
    }
