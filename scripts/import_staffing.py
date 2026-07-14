import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal
from app.models.facility import Facility
from app.services.cms_staffing_import import import_staffing_data


def main() -> None:
    db = SessionLocal()
    try:
        mapping = {f.cms_id: f.id for f in db.query(Facility).filter(Facility.state == "FL").all()}
        summary = import_staffing_data(db, mapping, state="FL")
        print(summary)
    finally:
        db.close()


if __name__ == "__main__":
    main()
