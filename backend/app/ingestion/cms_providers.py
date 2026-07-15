from typing import Dict, Set

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

SOURCE_NAME = "CMS Provider Information"


def import_providers(db: Session, state: str = "FL", limit: int = 100) -> Dict[str, int]:
    file_path = download_dataset(CMS_PROVIDER_DATASET_ID, "provider_information.csv")

    db.query(Facility).filter(Facility.state == state).delete()
    db.commit()

    ccn_to_facility_id: Dict[str, int] = {}
    imported = 0

    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue
        if imported >= limit:
            break

        ccn = row.get("CMS Certification Number (CCN)")
        name = row.get("Provider Name")
        if not ccn or not name:
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
            source_name=SOURCE_NAME,
            source_date=row.get("Processing Date"),
            confidence_level="high",
        )
        db.add(facility)
        db.flush()

        ccn_to_facility_id[ccn] = facility.id
        imported += 1

    db.commit()
    return ccn_to_facility_id


def get_allowed_ccns(ccn_to_facility_id: Dict[str, int]) -> Set[str]:
    return set(ccn_to_facility_id.keys())
