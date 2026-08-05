import unittest

from app.simulations.realistic_synthetic_facilities import (
    load_synthetic_dataset,
    run_synthetic_decision_simulation,
    validate_synthetic_dataset,
)


class RealisticSyntheticDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = load_synthetic_dataset()

    def test_sparse_distribution_contract(self) -> None:
        validation = validate_synthetic_dataset(self.dataset)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(len(validation["facility_coverage"]), 10)
        self.assertGreaterEqual(validation["contradiction_count"], 3)
        self.assertEqual(
            set(validation["evidence_states"]),
            {
                "CONTRADICTED", "FACILITY_CLAIMED", "FACILITY_DOCUMENTED",
                "GOVERNMENT_VERIFIED", "NOT_APPLICABLE", "PROXY_SUPPORTED",
                "STALE_OFFICIAL", "THIRD_PARTY_DOCUMENTED", "UNKNOWN",
            },
        )

    def test_engine_distinguishes_fit_from_profile_completeness(self) -> None:
        report = run_synthetic_decision_simulation(self.dataset)
        self.assertTrue(report["pass"], report["assertions"])
        self.assertTrue(all(report["assertions"].values()))


if __name__ == "__main__":
    unittest.main()