from __future__ import annotations

import unittest
from unittest.mock import patch

from app.database import Base, SessionLocal, engine
import app.models.facility_outreach  # noqa: F401 -- registers tables on Base
from app.services.facility_contact_discovery_service import discover_contact, get_known_contact

Base.metadata.create_all(bind=engine)


class FacilityContactDiscoveryServiceTests(unittest.TestCase):
    def _db(self):
        return SessionLocal()

    def test_unknown_canonical_facility_returns_none(self) -> None:
        db = self._db()
        try:
            with patch(
                "app.services.facility_contact_discovery_service.get_canonical_facility_index",
                return_value={},
            ):
                self.assertIsNone(discover_contact(db, "does-not-exist"))
        finally:
            db.close()

    def test_no_official_website_found_returns_none(self) -> None:
        db = self._db()
        try:
            with patch(
                "app.services.facility_contact_discovery_service.get_canonical_facility_index",
                return_value={"canonical-a": {"facility_name": "Sunrise Manor", "city": "Las Vegas"}},
            ), patch(
                "app.services.facility_contact_discovery_service._candidate_official_url",
                return_value=None,
            ):
                self.assertIsNone(discover_contact(db, "canonical-a"))
        finally:
            db.close()

    def test_finds_and_prefers_marketing_email_over_general(self) -> None:
        db = self._db()
        homepage_html = """
        <html><body>
        <a href="mailto:info@example-facility.com">Email us</a>
        <a href="/contact-us">Contact</a>
        </body></html>
        """
        contact_page_html = """
        <html><body>
        Reach our marketing team at marketing@example-facility.com for tours.
        </body></html>
        """

        def fake_fetch(url: str):
            if url == "https://example-facility.com":
                return homepage_html, 200
            if url == "https://example-facility.com/contact-us":
                return contact_page_html, 200
            return "", 404

        db.query(app.models.facility_outreach.FacilityContact).delete()
        db.commit()

        with patch(
            "app.services.facility_contact_discovery_service.get_canonical_facility_index",
            return_value={"canonical-b": {"facility_name": "Example Facility", "city": "Las Vegas"}},
        ), patch(
            "app.services.facility_contact_discovery_service._candidate_official_url",
            return_value="https://example-facility.com",
        ), patch(
            "app.services.facility_contact_discovery_service._fetch",
            side_effect=fake_fetch,
        ):
            contact = discover_contact(db, "canonical-b")

        try:
            self.assertIsNotNone(contact)
            self.assertEqual(contact.email, "marketing@example-facility.com")
            self.assertEqual(contact.contact_role, "MARKETING_SALES")
            self.assertEqual(contact.source_url, "https://example-facility.com/contact-us")

            # Second call must reuse the stored contact, not re-fetch anything.
            with patch("app.services.facility_contact_discovery_service._fetch") as mock_fetch:
                reused = discover_contact(db, "canonical-b")
            mock_fetch.assert_not_called()
            self.assertEqual(reused.id, contact.id)
            self.assertEqual(get_known_contact(db, "canonical-b").id, contact.id)
        finally:
            db.close()

    def test_asset_filename_false_positive_is_ignored(self) -> None:
        db = self._db()
        homepage_html = '<img srcset="hero@2x.png 2x">'
        with patch(
            "app.services.facility_contact_discovery_service.get_canonical_facility_index",
            return_value={"canonical-c": {"facility_name": "No Email Facility", "city": "Las Vegas"}},
        ), patch(
            "app.services.facility_contact_discovery_service._candidate_official_url",
            return_value="https://no-email-facility.com",
        ), patch(
            "app.services.facility_contact_discovery_service._fetch",
            return_value=(homepage_html, 200),
        ):
            contact = discover_contact(db, "canonical-c")
        try:
            self.assertIsNone(contact)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
