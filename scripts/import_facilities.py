import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal
from app.services.cms_provider_import import import_provider_information


def main() -> None:
    db = SessionLocal()
    try:
        _, summary = import_provider_information(db, state="FL", limit=100)
        print(summary)
    finally:
        db.close()


if __name__ == "__main__":
    main()
