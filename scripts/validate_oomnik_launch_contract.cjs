const assert = require('node:assert/strict');
const { scenarios } = require('../frontend/tests/browser/launch-scenarios.cjs');
const { validateLaunchContract } = require('../frontend/tests/browser/launch-contract.cjs');

assert.equal(Object.keys(scenarios).length, 10, 'The launch corpus must contain exactly ten canonical journeys.');

const scenario = scenarios.memory_mom;
const must_haves = scenario.expectedMustKeys.map((key) => ({ key }));
const good = {
  patient_needs_profile: { decision_intelligence: { client_intent: { must_haves } } },
  decision_intelligence: {
    recommendation_execution_allowed: true,
    canonical_decision_state: { phase: 'PROVISIONAL_RECOMMENDATION' },
    facility_selection_pipeline: { ai_ranking: { required: true, status: 'COMPLETE' } },
    client_statement_accounting: { dropped_count: 0, coverage_percent: 100 },
  },
  results: [{
    facility_name: 'Safe Memory Community', eligibility_status: 'ELIGIBLE', must_eligibility: 'MUST_ELIGIBLE',
    client_intent_fit: { hard_gate: 'PASS', must_fail: [], must_unknown: [] },
  }],
};
validateLaunchContract({
  scenarioName: 'memory_mom', scenario, payload: good,
  resultsText: 'Medication management is supported. Help with daily activities is supported. Memory care is supported. Confirm availability, pricing and Medicaid.',
});

assert.throws(() => validateLaunchContract({
  scenarioName: 'memory_mom', scenario,
  payload: { ...good, patient_needs_profile: { decision_intelligence: { client_intent: { must_haves: [...must_haves, { key: 'SEMANTIC_FUTURE_CARE_PATH' }] } } } },
  resultsText: 'Medication management is supported. Medication support is not verified. Confirm availability only.',
}), /spurious client MUST|customer-visible gap missing|contradictory customer copy/);

assert.throws(() => validateLaunchContract({
  scenarioName: 'memory_mom', scenario,
  payload: { ...good, decision_intelligence: { ...good.decision_intelligence, recommendation_execution_allowed: false } },
  resultsText: 'Medication management is supported. Help with daily activities is supported. Memory care is supported. Confirm availability, pricing and Medicaid.',
}), /recommendation execution is blocked/);

console.log('OOMNIK_LAUNCH_CONTRACT=PASS scenarios=10 contradiction_guard=PASS coverage_guard=PASS');
