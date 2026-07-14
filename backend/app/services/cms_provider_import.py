from typing import Dict, Tuple

from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.services.cms_service import (
    CMS_PROVIDER_DATASET_ID,
    clean_state,
    download_dataset,
    iter_csv_rows,
    to_float,
    to_int,
)


def import_provider_information(db: Session, state: str = "FL", limit: int = 100) -> Tuple[Dict[str, int], dict]:
    file_path = download_dataset(CMS_PROVIDER_DATASET_ID, "provider_information.csv")

    existing = db.query(Facility).filter(Facility.state == state).all()
    for facility in existing:
        db.delete(facility)
    db.commit()

    ccn_to_facility_id: Dict[str, int] = {}
    imported = 0
    missing_records = 0

    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue
        if imported >= limit:
            break

        ccn = row.get("CMS Certification Number (CCN)")
        name = row.get("Provider Name")
        if not ccn or not name:
            missing_records += 1
            continue

        facility = Facility(
            cms_id=ccn,
            name=name,
            address=row.get("Provider Address") or "",
            city=row.get("City/Town") or "",
            state=state,
            zip_code=row.get("ZIP Code") or "",
            phone=row.get("Telephone Number"),
            overall_rating=to_int(row.get("Overall Rating")),
            staffing_rating=to_int(row.get("Staffing Rating")),
            quality_rating=to_int(row.get("QM Rating")),
            inspection_rating=to_int(row.get("Health Inspection Rating")),
            beds=to_int(row.get("Number of Certified Beds")),
            latitude=to_float(row.get("Latitude")),
            longitude=to_float(row.get("Longitude")),
        )
        db.add(facility)
        db.flush()

        ccn_to_facility_id[ccn] = facility.id
        imported += 1

    db.commit()

    summary = {
        "facilities_imported": imported,
        "missing_records": missing_records,
        "failed_mappings": 0,
    }
    return ccn_to_facility_id, summary
