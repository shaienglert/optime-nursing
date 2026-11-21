from __future__ import annotations

import io
import os
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient
from PIL import Image

from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.models.facility import Facility, FacilityAuditLog, FacilityPhoto, FacilityUser
from app.services.photo_storage import _normalise

CMS_ID = "TEST-PHOTO-UPLOAD"


def _jpeg(width: int = 3000, height: int = 2000, gps: bool = False) -> bytes:
    image = Image.new("RGB", (width, height), (120, 160, 200))
    out = io.BytesIO()
    exif = Image.Exif()
    if gps:
        exif[0x8825] = {1: "N", 2: (32.0, 5.0, 0.0)}
    image.save(out, format="JPEG", exif=exif)
    return out.getvalue()


class PhotoNormaliseTests(unittest.TestCase):
    def test_resizes_and_strips_metadata(self) -> None:
        result = Image.open(io.BytesIO(_normalise(_jpeg(gps=True))))
        self.assertEqual(result.format, "JPEG")
        self.assertLessEqual(max(result.size), 1600)
        self.assertEqual(len(result.getexif()), 0)

    def test_png_is_accepted(self) -> None:
        out = io.BytesIO()
        Image.new("RGBA", (50, 50)).save(out, format="PNG")
        self.assertEqual(Image.open(io.BytesIO(_normalise(out.getvalue()))).format, "JPEG")

    def test_non_image_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _normalise(b"<html>not an image</html>")
        with self.assertRaises(ValueError):
            _normalise(b"")


class PhotoUploadEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"OPTIME_UPLOAD_DIR": self.tmp.name})
        self.env.start()
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self._clean()
        self.facility = Facility(cms_id=CMS_ID, name="Photo Test", address="x", city="x", state="IL", zip_code="0")
        self.db.add(self.facility)
        self.db.commit()
        self.owner = FacilityUser(facility_id=self.facility.id, email="o@example.com", password_hash="x", role="OWNER")
        self.medical = FacilityUser(facility_id=self.facility.id, email="d@example.com", password_hash="x", role="ACTIVITIES")
        self.db.add_all([self.owner, self.medical])
        self.db.commit()
        from app.main import app

        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._clean()
        self.db.close()
        self.env.stop()
        self.tmp.cleanup()

    def _clean(self) -> None:
        ids = [f.id for f in self.db.query(Facility).filter(Facility.cms_id == CMS_ID)]
        if ids:
            for model in (FacilityPhoto, FacilityAuditLog, FacilityUser):
                self.db.query(model).filter(model.facility_id.in_(ids)).delete(synchronize_session=False)
            self.db.query(Facility).filter(Facility.id.in_(ids)).delete(synchronize_session=False)
        self.db.commit()

    def _upload(self, user_id: int, data: bytes):
        return self.client.post(
            f"/provider/facilities/{self.facility.id}/photos/upload",
            data={"user_id": str(user_id)},
            files={"file": ("p.jpg", data, "image/jpeg")},
        )

    def test_upload_serve_and_remove(self) -> None:
        response = self._upload(self.owner.id, _jpeg())
        self.assertEqual(response.status_code, 200, response.text)
        url = response.json()["url"]
        self.assertTrue(url.startswith(f"/media/facility_photos/{self.facility.id}/"))

        served = self.client.get(url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.headers["content-type"], "image/jpeg")

        photo_id = response.json()["photo_id"]
        removed = self.client.request(
            "DELETE", f"/provider/facilities/{self.facility.id}/photos/{photo_id}", json={"user_id": self.owner.id}
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_role_without_photo_permission_writes_nothing(self) -> None:
        response = self._upload(self.medical.id, _jpeg())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(any(os.scandir(self.tmp.name)))

    def test_foreign_user_is_refused(self) -> None:
        self.assertEqual(self._upload(999999, _jpeg()).status_code, 403)

    def test_bad_file_gets_hebrew_reason(self) -> None:
        response = self._upload(self.owner.id, b"not an image")
        self.assertEqual(response.status_code, 400)
        self.assertIn("תמונה", response.json()["detail"])

    def test_path_traversal_is_not_served(self) -> None:
        self.assertEqual(self.client.get(f"/media/facility_photos/{self.facility.id}/..%2F..%2Fetc").status_code, 404)


if __name__ == "__main__":
    unittest.main()
