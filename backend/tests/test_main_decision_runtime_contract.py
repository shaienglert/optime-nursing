from __future__ import annotations

import importlib
import unittest


class MainDecisionRuntimeContractTests(unittest.TestCase):
    def test_main_imports_integrated_decision_runtime_contract(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")

        self.assertTrue(hasattr(decision, "_regulatory_index"))
        self.assertTrue(callable(decision._regulatory_index))
        self.assertTrue(callable(decision.build_patient_needs_profile))
        self.assertTrue(callable(decision.build_patient_comparison_context))
        self.assertTrue(callable(decision.run_patient_decision_engine))
        self.assertIsNotNone(main.app)


if __name__ == "__main__":
    unittest.main()
