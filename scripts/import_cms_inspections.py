import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal
from app.ingestion.cms_providers import import_providers
from app.ingestion.cms_inspections import import_inspections


def main() -> None:
    db = SessionLocal()
    try:
        mapping = import_providers(db, state="FL", limit=100)
        import_inspections(db, mapping, state="FL")
        print({"inspections_imported_for_facilities": len(mapping)})
    finally:
        db.close()


if __name__ == "__main__":
    main()
