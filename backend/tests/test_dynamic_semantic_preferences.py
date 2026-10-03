from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.semantic_preference_runtime import (
    build_dynamic_preference_model,
    build_facility_claim_ledger,
    verify_dynamic_preferences,
)


class DynamicSemanticPreferenceTests(unittest.TestCase):
    def _human(self):
        return {
            "semantic_ai": {
                "result": {
                    "preferences": [
                        "She wants a serious bridge club with regular games",
                        "She values access to gardening and outdoor horticulture",
                    ],
                    "statements": [
                        {
                            "raw_text": "Hebrew-speaking staff would make her feel at home",
                            "meaning": "Access to Hebrew-speaking staff",
                            "importance": "NICE",
                            "knowledge_state": "KNOWN",
                            "status": "USED",
                        },
                        {
                            "raw_text": "She needs medication management",
                            "meaning": "Medication management",
                            "importance": "MUST",
                            "knowledge_state": "KNOWN",
                            "status": "USED",
                        },
                    ],
                }
            }
        }

    def _row(self):
        return {
            "canonical_facility_id": "FAC-1",
            "facility_name": "Example Community",
            "canonical_type": "ASSISTED_LIVING_RFG",
            "housing_modalities": ["ASSISTED_LIVING"],
            "care_setting_fit": {"status": "PRIMARY_FIT"},
            "provider_housing_evidence": {
                "evidence": {
                    "bridge_club_schedule": "Duplicate bridge Tuesdays and Fridays",
                    "garden_program": "Resident gardening group and raised beds",
                }
            },
            # Simulates a future evidence namespace added by another research worker.
            # The preference engine must ingest it without a code change.
            "future_research_evidence_v99": {
                "observatory_outings": "Monthly dark-sky astronomy outing documented by provider calendar"
            },
            "client_intent_fit": {"public_reputation": {}},
        }

    def test_arbitrary_preferences_become_dynamic_dimensions_without_catalog(self):
        model = build_dynamic_preference_model(self._human())
        meanings = {row["semantic_meaning"] for row in model["preferences"]}
        self.assertEqual(model["preference_count"], 3)
        self.assertIn("She wants a serious bridge club with regular games", meanings)
        self.assertIn("She values access to gardening and outdoor horticulture", meanings)
        self.assertIn("Access to Hebrew-speaking staff", meanings)
        self.assertTrue(model["hard_coded_preference_catalog_forbidden"])
        self.assertEqual(len({row["preference_id"] for row in model["preferences"]}), 3)

    def test_claim_ledger_is_generic_and_accepts_future_evidence_namespaces(self):
        ledger = build_facility_claim_ledger(self._row())
        paths = {claim["path"] for claim in ledger["claims"]}
        self.assertTrue(any("bridge_club_schedule" in path for path in paths))
        self.assertTrue(any("garden_program" in path for path in paths))
        self.assertTrue(any("future_research_evidence_v99.observatory_outings" in path for path in paths))
        self.assertEqual(ledger["source_model"], "COMPLETE_GOVERNED_CANDIDATE_RECORD")

    def test_ai_cannot_assert_match_without_governed_claim(self):
        model = build_dynamic_preference_model({"semantic_ai": {"result": {"preferences": ["A quiet astronomy club"], "statements": []}}})
        row = self._row()
        bad_packet = {
            "assessments": [
                {
                    "preference_id": model["preferences"][0]["preference_id"],
                    "status": "MATCH",
                    "supporting_claim_ids": [],
                    "reason": "sounds plausible",
                    "provider_question_if_unknown": None,
                }
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "1"}, clear=False), patch(
            "app.services.semantic_preference_runtime._default_transport", return_value=bad_packet
        ):
            with self.assertRaisesRegex(RuntimeError, "AI_PREFERENCE_VERIFICATION_REQUIRED_FAILED"):
                verify_dynamic_preferences([row], model)

    def test_arbitrary_preferences_can_match_only_by_citing_existing_claims(self):
        human = {"semantic_ai": {"result": {"preferences": ["Regular bridge games", "Resident gardening"], "statements": []}}}
        model = build_dynamic_preference_model(human)
        row = self._row()
        ledger = build_facility_claim_ledger(row)
        bridge_claim = next(c["claim_id"] for c in ledger["claims"] if "bridge_club_schedule" in c["path"])
        garden_claim = next(c["claim_id"] for c in ledger["claims"] if "garden_program" in c["path"])
        packet = {
            "assessments": [
                {
                    "preference_id": model["preferences"][0]["preference_id"],
                    "status": "MATCH",
                    "supporting_claim_ids": [bridge_claim],
                    "reason": "The governed schedule explicitly documents regular bridge games.",
                    "provider_question_if_unknown": None,
                },
                {
                    "preference_id": model["preferences"][1]["preference_id"],
                    "status": "MATCH",
                    "supporting_claim_ids": [garden_claim],
                    "reason": "The governed evidence explicitly documents resident gardening.",
                    "provider_question_if_unknown": None,
                },
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "1"}, clear=False), patch(
            "app.services.semantic_preference_runtime._default_transport", return_value=packet
        ):
            summary = verify_dynamic_preferences([row], model)
        self.assertEqual(row["nice_to_have_coverage"]["status"], "NICE_COMPLETE")
        self.assertEqual(summary["nice_complete_candidate_count"], 1)

    def test_not_applicable_preference_does_not_block_completeness(self):
        # Reproduces the production pattern: a client value/goal ("preserve
        # independence") sits alongside a genuinely checkable preference. The
        # checkable one matching should be enough for NICE_COMPLETE -- an
        # unverifiable preference must never be required to MATCH.
        human = {"semantic_ai": {"result": {"preferences": ["Regular bridge games", "Preserve independence"], "statements": []}}}
        model = build_dynamic_preference_model(human)
        row = self._row()
        ledger = build_facility_claim_ledger(row)
        bridge_claim = next(c["claim_id"] for c in ledger["claims"] if "bridge_club_schedule" in c["path"])
        packet = {
            "assessments": [
                {
                    "preference_id": model["preferences"][0]["preference_id"],
                    "status": "MATCH",
                    "supporting_claim_ids": [bridge_claim],
                    "reason": "The governed schedule explicitly documents regular bridge games.",
                    "provider_question_if_unknown": None,
                },
                {
                    "preference_id": model["preferences"][1]["preference_id"],
                    "status": "NOT_APPLICABLE",
                    "supporting_claim_ids": [],
                    "reason": "This describes a client goal, not a checkable fact about any facility.",
                    "provider_question_if_unknown": None,
                },
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "1"}, clear=False), patch(
            "app.services.semantic_preference_runtime._default_transport", return_value=packet
        ):
            summary = verify_dynamic_preferences([row], model)
        self.assertEqual(row["nice_to_have_coverage"]["status"], "NICE_COMPLETE")
        self.assertEqual(summary["nice_complete_candidate_count"], 1)
        self.assertEqual(summary["verification_required_count"], 0)
        self.assertNotIn(model["preferences"][1]["preference_id"], row["nice_to_have_coverage"]["unresolved"])

    def test_all_preferences_not_applicable_is_trivially_complete(self):
        # If every extracted "preference" turns out to be an unverifiable client
        # value/goal, completeness must not be permanently unreachable -- there is
        # nothing left to check, so this is complete by definition.
        human = {"semantic_ai": {"result": {"preferences": ["Preserve independence", "Least restrictive setting"], "statements": []}}}
        model = build_dynamic_preference_model(human)
        row = self._row()
        packet = {
            "assessments": [
                {
                    "preference_id": pref["preference_id"],
                    "status": "NOT_APPLICABLE",
                    "supporting_claim_ids": [],
                    "reason": "Client value/goal, not a checkable facility fact.",
                    "provider_question_if_unknown": None,
                }
                for pref in model["preferences"]
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "1"}, clear=False), patch(
            "app.services.semantic_preference_runtime._default_transport", return_value=packet
        ):
            summary = verify_dynamic_preferences([row], model)
        self.assertEqual(row["nice_to_have_coverage"]["status"], "NICE_COMPLETE")
        self.assertEqual(summary["nice_complete_candidate_count"], 1)
        self.assertEqual(summary["verification_required_count"], 0)

    def test_missing_evidence_stays_unknown_not_negative(self):
        model = build_dynamic_preference_model({"semantic_ai": {"result": {"preferences": ["Weekly astronomy lectures"], "statements": []}}})
        row = self._row()
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "0", "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "0"}, clear=False):
            summary = verify_dynamic_preferences([row], model)
        self.assertEqual(row["nice_to_have_coverage"]["status"], "NICE_UNVERIFIED")
        self.assertEqual(row["dynamic_preference_fit"]["assessments"][0]["status"], "UNKNOWN")
        self.assertEqual(summary["verification_required_count"], 1)




class TracedProductionPreferenceTests(unittest.TestCase):
    def _packet(self, statements, preferences):
        return {'semantic_ai': {'result': {
            'wire_contract': {'version': 'semantic-extraction-v1', 'schema_constrained': True},
            'statements': statements, 'preferences': preferences,
        }}}

    def test_distinct_sources_with_one_generic_gloss_remain_separate_obligations(self):
        from app.services.must_ai_nice_pipeline import _defer_dynamic_preference_verification
        expressions = ['Lunar astronomy club', 'Glacier microscopy seminars']
        traces = [{'raw_text': value, 'meaning': 'A preferred facility activity',
                   'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED',
                   'mapped_parameters': []} for value in expressions]
        model = build_dynamic_preference_model(self._packet([*traces, traces[0]], []))
        self.assertEqual(model['preference_count'], 2)
        self.assertEqual([pref['client_expression'] for pref in model['preferences']], expressions)
        self.assertEqual(len({pref['preference_id'] for pref in model['preferences']}), 2)
        self.assertEqual(model, build_dynamic_preference_model(self._packet([*traces, traces[0]], [])))
        rows = [{}]
        _defer_dynamic_preference_verification(rows, model)
        assessments = rows[0]['dynamic_preference_fit']['assessments']
        self.assertEqual([a['status'] for a in assessments], ['UNKNOWN', 'UNKNOWN'])
        self.assertTrue(all(value in assessment['provider_question_if_unknown']
                            for value, assessment in zip(expressions, assessments)))

    def test_same_canonical_selection_has_one_stable_identity_across_model_glosses(self):
        def trace(path, meaning):
            return {'raw_text': 'Glacier microscopy seminars', 'meaning': meaning,
                    'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED',
                    'mapped_parameters': [path]}
        primary = trace('happinessPreferences', 'Preferred seminars')
        alias = trace('humanIntelligenceV2.socialProfile.hobbyParticipation', 'Microscopy hobby participation')
        model = build_dynamic_preference_model(self._packet([primary, alias], []))
        self.assertEqual(model['preference_count'], 1)
        other = build_dynamic_preference_model(self._packet([alias], []))
        self.assertEqual(model['preferences'][0]['preference_id'], other['preferences'][0]['preference_id'])

    def test_known_selected_slot_has_one_identity_despite_extra_or_missing_ai_paths(self):
        expression = 'Glacier microscopy seminars'
        traces = [{'raw_text': expression, 'meaning': meaning, 'importance': 'NICE',
                   'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': paths}
                  for meaning, paths in [('Preferred seminar', ['happinessPreferences']),
                                         ('Another generic gloss', []),
                                         ('A related interpretation', ['happinessPreferences', 'otherInterests'])]]
        human = self._packet(traces, [])
        human['canonical_decision_questionnaire'] = {
            'happinessPreferences': [expression],
            'humanIntelligenceV2': {'socialProfile': {'activityRequirementLevel': 'Preference'}}}
        model = build_dynamic_preference_model(human)
        self.assertEqual(model['preference_count'], 1)
        self.assertEqual(model['preferences'][0]['client_expression'], expression)

    def test_equal_literal_values_in_different_selected_slots_remain_distinct(self):
        from app.services.semantic_intent_ai import _selected_facility_property_traces
        expression = 'Shared arbitrary value'
        state = {'happinessPreferences': [expression], 'nearbyPlaces': [expression],
                 'nearbyPlacesImportance': 'Nice to have',
                 'humanIntelligenceV2': {'socialProfile': {'activityRequirementLevel': 'Preference'}}}
        selections = _selected_facility_property_traces(state)
        self.assertEqual({s['path'] for s in selections}, {'happinessPreferences', 'nearbyPlaces'})
        traces = [{'raw_text': expression, 'meaning': 'A selected property', 'importance': 'NICE',
                   'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': [s['path']]}
                  for s in selections]
        human = self._packet(traces, [])
        human['canonical_decision_questionnaire'] = state
        self.assertEqual(build_dynamic_preference_model(human)['preference_count'], 2)

    def test_one_narrative_quote_can_still_have_distinct_unmapped_meanings(self):
        traces = [{'raw_text': 'She wants bridge and gardening.', 'meaning': meaning,
                   'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED',
                   'mapped_parameters': []} for meaning in ['Organized bridge games', 'Resident gardening program']]
        self.assertEqual(build_dynamic_preference_model(self._packet(traces, []))['preference_count'], 2)

    def test_typed_control_values_do_not_become_provider_properties(self):
        traces = [{'raw_text': quote, 'meaning': 'A preferred facility feature',
                   'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED',
                   'mapped_parameters': [path]} for path, quote in [
            ('humanIntelligenceV2.futureCareProfile.continuumOfCarePreference', 'Preferred'),
            ('nearbyPlacesImportance', 'Nice to have')]]
        model = build_dynamic_preference_model(self._packet(traces, []))
        self.assertEqual(model['preference_count'], 0)

    def test_unverified_question_preserves_interpretation_and_literal_selection(self):
        from app.services.must_ai_nice_pipeline import _defer_dynamic_preference_verification
        trace = {'raw_text': 'Weekly', 'meaning': 'Organized social activities at least once a week',
                 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED',
                 'mapped_parameters': ['humanIntelligenceV2.socialProfile.socialInteractionFrequency']}
        model = build_dynamic_preference_model(self._packet([trace], []))
        rows = [{}]
        _defer_dynamic_preference_verification(rows, model)
        question = rows[0]['dynamic_preference_fit']['assessments'][0]['provider_question_if_unknown']
        self.assertIn(trace['meaning'], question)
        self.assertIn(trace['raw_text'], question)

    def test_live_verification_fallback_questions_preserve_distinct_source_specificity(self):
        expressions = ['Lunar astronomy club', 'Glacier microscopy seminars']
        traces = [{'raw_text': value, 'meaning': 'A preferred facility activity',
                   'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED',
                   'mapped_parameters': []} for value in expressions]
        model = build_dynamic_preference_model(self._packet(traces, []))
        rows = [{}]
        with patch.dict(os.environ, {'OPTIME_SEMANTIC_AI_ENABLED': '0'}):
            verify_dynamic_preferences(rows, model)
        assessments = rows[0]['dynamic_preference_fit']['assessments']
        self.assertEqual(len(assessments), 2)
        self.assertTrue(all(value in assessment['provider_question_if_unknown']
                            for value, assessment in zip(expressions, assessments)))

    def test_advisory_paraphrase_cannot_bypass_excluded_control_and_context_traces(self):
        statements = [
            {'raw_text': 'No preference', 'meaning': 'Community size preference is no preference.', 'importance': 'CONTEXT', 'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': ['humanIntelligenceV2.personalityProfile.communitySizePreference']},
            {'raw_text': 'Preference', 'meaning': 'Activity requirement level is preference.', 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': ['humanIntelligenceV2.socialProfile.activityRequirementLevel']},
            {'raw_text': 'Cautious but open', 'meaning': 'Cautious about moving.', 'importance': 'CONTEXT', 'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': []},
        ]
        packet = self._packet(statements, ['No preference for community size', 'Preference for activity requirement level', 'Open but cautious about a move'])
        model = build_dynamic_preference_model(packet)
        self.assertEqual(model['preference_count'], 0)
        self.assertEqual(model['preference_authority'], 'QUOTED_STATEMENT_TRACES')
        self.assertEqual(packet['semantic_ai']['result']['statements'], statements)
        self.assertEqual(len(packet['semantic_ai']['result']['preferences']), 3)

    def test_arbitrary_traced_preference_remains_open_ended_without_summary_or_mapping(self):
        statements = [{'raw_text': 'A lunar astronomy discussion club', 'meaning': 'Regular lunar astronomy discussions', 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': []}]
        model = build_dynamic_preference_model(self._packet(statements, []))
        self.assertEqual(model['preference_count'], 1)
        self.assertEqual(model['preferences'][0]['semantic_meaning'], statements[0]['meaning'])
        self.assertEqual(model['preferences'][0]['source'], 'semantic_ai.statements')

    def test_traced_preference_has_one_dimension_despite_summary_paraphrases(self):
        statements = [{'raw_text': 'Low sodium', 'meaning': 'Low sodium diet', 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': ['humanIntelligenceV2.foodProfile.dietaryPreferences']}]
        model = build_dynamic_preference_model(self._packet(statements, ['Low sodium diet.', 'Dietary preference is low sodium']))
        self.assertEqual(model['preference_count'], 1)

    def test_property_quote_is_retained_even_when_it_also_maps_an_importance_control(self):
        statements = [{'raw_text': 'Enjoys glacier microscopy seminars', 'meaning': 'Glacier microscopy seminars are preferred', 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED', 'mapped_parameters': ['humanIntelligenceV2.socialProfile.activityRequirementLevel']}]
        model = build_dynamic_preference_model(self._packet(statements, []))
        self.assertEqual(model['preference_count'], 1)
        self.assertEqual(model['preferences'][0]['client_expression'], statements[0]['raw_text'])


if __name__ == "__main__":
    unittest.main()
