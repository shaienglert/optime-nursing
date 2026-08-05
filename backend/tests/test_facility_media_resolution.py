import unittest

from app.services.facility_media_registry import build_visual_media_payload
from app.services.facility_media_resolution import (
    classify_search_result,
    evaluate_identity_candidate,
    resolve_best_identity,
    select_primary_image,
)


class IdentityResolutionTests(unittest.TestCase):
    def test_search_result_classification_never_promotes_directory(self) -> None:
        self.assertEqual(
            classify_search_result("https://www.seniorly.com/facility/riverside", "Exact facility details"),
            "DIRECTORY",
        )

    def test_generic_token_false_match_is_rejected(self) -> None:
        result = evaluate_identity_candidate(
            facility_name="CORAL GABLES NURSING AND REHABILITATION CENTER",
            name_variants=[],
            address="7060 SW 8TH STREET",
            city="MIAMI",
            state="FL",
            phone="3052611363",
            cms_ccn="105005",
            operator_name="",
            candidate_url="https://en.wikipedia.org/wiki/Coral",
            page_text="Coral are marine invertebrates in the class Anthozoa.",
            source_type="SEARCH_DISCOVERY",
        )

        self.assertEqual(result["status"], "NOT_VERIFIED")

    def test_address_and_phone_verify_identity_despite_name_variation(self) -> None:
        result = evaluate_identity_candidate(
            facility_name="KENDALL LAKES HEALTHCARE AND REHAB CENTER",
            name_variants=["KENDALL LAKES HEALTH AND REHABILITATION CENTER"],
            address="5280 SW 157 AVENUE",
            city="MIAMI",
            state="FL",
            phone="7864337400",
            cms_ccn="686123",
            operator_name="",
            candidate_url="https://www.kendallhrc.com/",
            page_text=(
                "Kendall Lakes Health and Rehabilitation Center 5280 SW 157th Ave Miami FL 33185 "
                "Call us at 786-433-7400 for skilled nursing and rehabilitation care."
            ),
            source_type="SEARCH_DISCOVERY",
        )

        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["identity_match_evidence"]["phone_match"])

    def test_search_directory_is_not_mislabeled_as_official_site(self) -> None:
        result = evaluate_identity_candidate(
            facility_name="WEST GABLES HEALTH CARE CENTER",
            name_variants=[],
            address="2525 SW 75TH AVENUE",
            city="MIAMI",
            state="FL",
            phone="3052659391",
            cms_ccn="105623",
            operator_name="",
            candidate_url="https://directory.example.com/west-gables-health-care-center",
            page_text=(
                "West Gables Health Care Center, 2525 SW 75th Avenue, Miami FL. "
                "Call 305-265-9391. CMS certification number 105623."
            ),
            source_type="SEARCH_DISCOVERY",
        )

        self.assertNotEqual(result["status"], "VERIFIED")

    def test_facility_named_directory_subdomain_is_not_official(self) -> None:
        result = evaluate_identity_candidate(
            facility_name="LIFE CARE CENTER OF MELBOURNE",
            name_variants=[],
            address="606 E SHERIDAN RD",
            city="MELBOURNE",
            state="FL",
            phone="3217273844",
            cms_ccn="105291",
            operator_name="",
            candidate_url="https://life-care-center-of-melbourne.seniorlivingflorida.org/",
            page_text=(
                "Life Care Center of Melbourne, 606 E Sheridan Rd, Melbourne FL. "
                "Call 321-727-3844. CMS certification number 105291."
            ),
            source_type="SEARCH_DISCOVERY",
        )

        self.assertNotEqual(result["status"], "VERIFIED")

    def test_generic_nursing_home_directory_domain_is_not_official(self) -> None:
        result = evaluate_identity_candidate(
            facility_name="CLIFFORD CHESTER SIMS STATE VETERANS NURSING HOME",
            name_variants=[],
            address="4419 TRAM ROAD",
            city="SPRINGFIELD",
            state="FL",
            phone="8507475401",
            cms_ccn="106056",
            operator_name="",
            candidate_url="https://www.nursinghomedatabase.com/snf/106056",
            page_text=(
                "Clifford Chester Sims State Veterans Nursing Home, 4419 Tram Road, Springfield FL. "
                "Call 850-747-5401. CMS certification number 106056."
            ),
            source_type="SEARCH_DISCOVERY",
        )

        self.assertNotEqual(result["status"], "VERIFIED")

    def test_resolve_best_identity_prefers_verified_domain(self) -> None:
        wrong = {
            "candidate_url": "https://kendall-jenner.net/",
            "status": "NOT_VERIFIED",
            "score": 0.08,
            "identity_match_evidence": {},
        }
        right = {
            "candidate_url": "https://www.kendallhrc.com/",
            "status": "VERIFIED",
            "score": 0.94,
            "identity_match_evidence": {"phone_match": True},
        }

        resolved = resolve_best_identity([wrong, right])
        self.assertEqual(resolved["identity_status"], "VERIFIED")
        self.assertEqual(resolved["official_website_url"], "https://www.kendallhrc.com/")

    def test_resolve_best_identity_uses_ranking_score_tiebreak(self) -> None:
        rehab = {
            "candidate_url": "https://www.westgablesrehab.com/",
            "status": "VERIFIED",
            "score": 1.0,
            "ranking_score": 1.04,
            "identity_match_evidence": {"domain_affinity_score": 0.5},
        }
        healthcare = {
            "candidate_url": "https://westgableshealthcare.com/",
            "status": "VERIFIED",
            "score": 1.0,
            "ranking_score": 1.08,
            "identity_match_evidence": {"domain_affinity_score": 1.0},
        }

        resolved = resolve_best_identity([rehab, healthcare])
        self.assertEqual(resolved["identity_status"], "VERIFIED")
        self.assertEqual(resolved["official_website_url"], "https://westgableshealthcare.com/")

    def test_resolve_best_identity_ignores_same_domain_duplicate(self) -> None:
        apex = {
            "candidate_url": "https://westgableshealthcare.com/",
            "status": "VERIFIED",
            "score": 1.0,
            "ranking_score": 1.064,
            "identity_match_evidence": {"domain_affinity_score": 0.8},
        }
        www = {
            "candidate_url": "https://www.westgableshealthcare.com/",
            "status": "VERIFIED",
            "score": 1.0,
            "ranking_score": 1.064,
            "identity_match_evidence": {"domain_affinity_score": 0.8},
        }
        rehab = {
            "candidate_url": "https://www.westgablesrehab.com/",
            "status": "VERIFIED",
            "score": 1.0,
            "ranking_score": 1.032,
            "identity_match_evidence": {"domain_affinity_score": 0.4},
        }

        resolved = resolve_best_identity([www, apex, rehab])
        self.assertEqual(resolved["identity_status"], "VERIFIED")
        self.assertEqual(resolved["official_website_url"], "https://www.westgableshealthcare.com/")


class ImageResolutionTests(unittest.TestCase):
    def test_award_badge_is_rejected(self) -> None:
        result = select_primary_image(
            [{"url": "https://melbournehc.com/uploads/top-work-place-badge.webp", "source_type": "OFFICIAL_PAGE_IMAGE", "alt_text": "Top workplace award", "source_page_url": "https://melbournehc.com/"}],
            facility_name="MELBOURNE HEALTHCARE AND REHABILITATION CENTER",
            official_page_url="https://melbournehc.com/",
        )
        self.assertEqual(result["image_status"], "UNKNOWN")

    def test_awards_graphic_with_full_page_title_alt_is_rejected(self) -> None:
        result = select_primary_image(
            [{"url": "https://melbournehc.com/uploads/regional-awards-multi-year.webp", "source_type": "OFFICIAL_OG_IMAGE", "alt_text": "Home | Melbourne Healthcare and Rehabilitation Center", "source_page_url": "https://melbournehc.com/"}],
            facility_name="MELBOURNE HEALTHCARE AND REHABILITATION CENTER",
            official_page_url="https://melbournehc.com/",
        )
        self.assertEqual(result["image_status"], "UNKNOWN")

    def test_generic_activity_photo_is_not_facility_specific(self) -> None:
        result = select_primary_image(
            [{"url": "https://spacecoasthc.com/uploads/activities.webp", "source_type": "OFFICIAL_PAGE_IMAGE", "alt_text": "", "source_page_url": "https://spacecoasthc.com/"}],
            facility_name="SPACE COAST HEALTHCARE AND REHABILITATION CENTER",
            official_page_url="https://spacecoasthc.com/",
        )
        self.assertNotEqual(result["image_status"], "VERIFIED")

    def test_generic_activity_photo_with_full_page_title_alt_is_not_verified(self) -> None:
        result = select_primary_image(
            [{"url": "https://spacecoasthc.com/uploads/activities.webp", "source_type": "OFFICIAL_OG_IMAGE", "alt_text": "Activities | Space Coast Healthcare and Rehabilitation Center", "source_page_url": "https://spacecoasthc.com/"}],
            facility_name="SPACE COAST HEALTHCARE AND REHABILITATION CENTER",
            official_page_url="https://spacecoasthc.com/",
        )
        self.assertNotEqual(result["image_status"], "VERIFIED")

    def test_single_name_token_without_physical_place_cue_is_not_verified(self) -> None:
        result = select_primary_image(
            [{"url": "https://windsorhrc.com/uploads/windsor-41.jpeg", "source_type": "OFFICIAL_PAGE_IMAGE", "alt_text": "", "source_page_url": "https://windsorhrc.com/"}],
            facility_name="WINDSOR HEALTH AND REHABILITATION CENTER",
            official_page_url="https://windsorhrc.com/",
        )
        self.assertNotEqual(result["image_status"], "VERIFIED")

    def test_stock_like_image_is_not_auto_verified(self) -> None:
        result = select_primary_image(
            [
                {
                    "url": "https://hialeahshoresrehab.com/wp-content/uploads/2022/11/pexels-yan-krukov-6815684.jpg",
                    "source_type": "OFFICIAL_PAGE_IMAGE",
                    "alt_text": "",
                    "source_page_url": "https://hialeahshoresrehab.com/",
                }
            ],
            facility_name="HIALEAH SHORES NURSING AND REHAB CENTER",
            official_page_url="https://hialeahshoresrehab.com/",
        )

        self.assertEqual(result["image_status"], "AMBIGUOUS")
        self.assertFalse(result["verified_facility_specific"])

    def test_short_extensionless_path_is_not_verified_by_facility_alt_text(self) -> None:
        result = select_primary_image(
            [
                {
                    "url": "https://royaloaksnursingandrehab.com/h",
                    "source_type": "OFFICIAL_PAGE_IMAGE",
                    "alt_text": "Royal Oaks Nursing and Rehab Center",
                    "source_page_url": "https://royaloaksnursingandrehab.com/about-us.php",
                }
            ],
            facility_name="ROYAL OAKS NURSING AND REHAB CENTER",
            official_page_url="https://royaloaksnursingandrehab.com/",
        )

        self.assertEqual(result["image_status"], "UNKNOWN")

    def test_full_facility_alt_does_not_verify_cropped_logo(self) -> None:
        result = select_primary_image(
            [{"url": "https://golfcresthc.com/uploads/cropped-golfcrest-copy.jpg", "source_type": "OFFICIAL_PAGE_IMAGE", "alt_text": "Golfcrest Nursing and Rehab Center", "source_page_url": "https://golfcresthc.com/"}],
            facility_name="GOLFCREST NURSING CENTER",
            official_page_url="https://golfcresthc.com/",
        )

        self.assertNotEqual(result["image_status"], "VERIFIED")

    def test_full_facility_alt_does_not_verify_generic_care_scene(self) -> None:
        result = select_primary_image(
            [{"url": "https://cdn.example.com/Rehab-at-Glades-01.webp", "source_type": "OFFICIAL_PAGE_IMAGE", "alt_text": "Glades West facility", "source_page_url": "https://gladeswestrehab.com/"}],
            facility_name="GLADES WEST REHABILITATION AND NURSING CENTER",
            official_page_url="https://gladeswestrehab.com/",
        )

        self.assertNotEqual(result["image_status"], "VERIFIED")

    def test_unverified_image_state_remains_unknown_when_no_candidates(self) -> None:
        result = select_primary_image([], facility_name="RIVERSIDE CARE CENTER", official_page_url="https://riversidecarecenter.com/")
        self.assertEqual(result["image_status"], "UNKNOWN")
        self.assertFalse(result["verified_facility_specific"])

    def test_named_hero_without_physical_place_cue_remains_ambiguous(self) -> None:
        result = select_primary_image(
            [
                {
                    "url": "https://westgableshealthcare.com/logo.svg",
                    "source_type": "OFFICIAL_PAGE_IMAGE",
                    "alt_text": "West Gables logo",
                    "source_page_url": "https://westgableshealthcare.com/",
                },
                {
                    "url": "https://cdn.sanity.io/images/xu1qs6w1/production/7f0c817940dbfd1738608a194638e7d05a714bed-1600x1065.jpg",
                    "source_type": "OFFICIAL_PAGE_IMAGE",
                    "alt_text": "home_hero - West Gables Health Care Center",
                    "source_page_url": "https://westgableshealthcare.com/",
                },
            ],
            facility_name="WEST GABLES HEALTH CARE CENTER",
            official_page_url="https://westgableshealthcare.com/",
        )

        self.assertEqual(result["image_status"], "AMBIGUOUS")
        self.assertFalse(result["verified_facility_specific"])


class MediaRegistryIntegrationTests(unittest.TestCase):
    def test_verified_registry_record_builds_visual_payload(self) -> None:
        payload = build_visual_media_payload(
            {
                "verified_facility_specific": True,
                "image_status": "VERIFIED",
                "primary_image_url": "https://riversidecarecenter.com/wp-content/uploads/2022/08/Riverside-edited-1.jpeg",
                "image_source_url": "https://riversidecarecenter.com/",
                "image_source_type": "OFFICIAL_PAGE_IMAGE",
                "display_rights_status": "OFFICIAL_DISPLAY_ALLOWED",
                "last_verified": "2026-07-22T00:00:00Z",
            }
        )

        self.assertIsNotNone(payload)
        self.assertEqual(payload["hero"]["url"], "https://riversidecarecenter.com/wp-content/uploads/2022/08/Riverside-edited-1.jpeg")

    def test_unverified_registry_record_does_not_build_visual_payload(self) -> None:
        payload = build_visual_media_payload(
            {
                "verified_facility_specific": False,
                "image_status": "AMBIGUOUS",
                "primary_image_url": "https://example.com/photo.jpg",
            }
        )
        self.assertIsNone(payload)

    def test_rights_uncertain_verified_record_does_not_build_visual_payload(self) -> None:
        payload = build_visual_media_payload(
            {
                "verified_facility_specific": True,
                "image_status": "VERIFIED",
                "primary_image_url": "https://example.com/photo.jpg",
                "display_rights_status": "OFFICIAL_SOURCE_TERMS_UNCLEAR",
            }
        )
        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()