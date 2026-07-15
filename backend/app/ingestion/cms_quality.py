from sqlalchemy.orm import Session

from app.models.facility import QualityMeasure
from app.services.cms_service import (
    CMS_QUALITY_DATASET_ID,
    clean_state,
    download_dataset,
    iter_csv_rows,
    to_float,
)

SOURCE_NAME = "CMS MDS Quality Measures"


def import_quality(db: Session, ccn_to_facility_id: dict, state: str = "FL") -> None:
    file_path = download_dataset(CMS_QUALITY_DATASET_ID, "quality_measures.csv")

    db.query(QualityMeasure).delete()
    db.commit()

    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue

        ccn = row.get("CMS Certification Number (CCN)") or ""
        facility_id = ccn_to_facility_id.get(ccn)
        if not facility_id:
            continue

        db.add(
            QualityMeasure(
                facility_id=facility_id,
                measure_code=row.get("Measure Code") or "UNKNOWN",
                measure_name=row.get("Measure Description") or "Unknown",
                measure_value=to_float(row.get("Four Quarter Average Score")),
                quality_rating=None,
                period_label=row.get("Measure Period") or "Unknown",
                source_name=SOURCE_NAME,
                source_date=row.get("Processing Date"),
                confidence_level="high",
            )
        )

    db.commit()
