const assert = require('node:assert/strict');

function clientIntent(payload) {
  return payload.patient_needs_profile?.decision_intelligence?.client_intent
    || payload.decision_intelligence?.client_intent
    || {};
}

function validateLaunchContract({ scenarioName, scenario, payload, resultsText }) {
  const violations = [];
  const mustKeys = new Set((clientIntent(payload).must_haves || []).map((item) => item.key));
  for (const key of scenario.expectedMustKeys || []) {
    if (!mustKeys.has(key)) violations.push(`missing client MUST: ${key}`);
  }
  for (const key of scenario.forbiddenMustKeys || []) {
    if (mustKeys.has(key)) violations.push(`spurious client MUST: ${key}`);
  }

  const verified = (payload.results || []).filter((item) =>
    item.must_eligibility ? item.must_eligibility === 'MUST_ELIGIBLE' : item.eligibility_status === 'ELIGIBLE');
  for (const item of verified) {
    const fit = item.client_intent_fit || {};
    if (fit.hard_gate && fit.hard_gate !== 'PASS') violations.push(`${item.facility_name}: verified card has hard_gate=${fit.hard_gate}`);
    if ((fit.must_fail || []).length) violations.push(`${item.facility_name}: verified card has failed MUST`);
    if ((fit.must_unknown || []).length) violations.push(`${item.facility_name}: verified card has unknown MUST`);
  }

  const decision = payload.decision_intelligence || {};
  const canonical = decision.canonical_decision_state || {};
  if (canonical.authoritative !== true) violations.push('canonical decision state is not authoritative');
  if (verified.length && canonical.can_show_recommendations !== true) {
    violations.push('verified results exist while canonical visibility is blocked');
  }
  if (verified.length && canonical.phase && !['PROVISIONAL_RECOMMENDATION', 'FINAL_RECOMMENDATION'].includes(canonical.phase)) {
    violations.push(`verified results conflict with canonical phase ${canonical.phase}`);
  }
  if (verified.length && canonical.ranking !== 'COMPLETE') {
    violations.push(`verified results conflict with canonical ranking ${canonical.ranking}`);
  }
  // Legacy fields remain output mirrors during migration, never authorities.  A
  // disagreement is still a serialization defect and must be visible immediately.
  if (typeof decision.recommendation_execution_allowed === 'boolean'
      && decision.recommendation_execution_allowed !== canonical.can_show_recommendations) {
    violations.push('legacy execution mirror diverges from canonical visibility');
  }
  for (const facilityName of scenario.forbiddenVerifiedFacilities || []) {
    if (verified.some((item) => item.facility_name === facilityName)) violations.push(`forbidden verified facility: ${facilityName}`);
  }

  const lower = String(resultsText || '').toLowerCase();
  for (const gap of scenario.requiredVisibleGaps || []) {
    if (!lower.includes(gap.toLowerCase())) violations.push(`customer-visible gap missing: ${gap}`);
  }
  const contradictionPairs = [
    ['medication management is supported', 'medication support is not verified'],
    ['help with daily activities is supported', 'adl support is not verified'],
    ['memory care is supported', 'memory care is not verified'],
  ];
  for (const [positive, negative] of contradictionPairs) {
    if (lower.includes(positive) && lower.includes(negative)) violations.push(`contradictory customer copy: ${positive} / ${negative}`);
  }

  const accounting = payload.decision_intelligence?.client_statement_accounting
    || payload.patient_needs_profile?.decision_intelligence?.human_intelligence?.semantic_ai?.statement_accounting;
  if (accounting) {
    if (Number(accounting.dropped_count || 0) !== 0) violations.push(`dropped client statements: ${accounting.dropped_count}`);
    if (accounting.coverage_percent != null && Number(accounting.coverage_percent) !== 100) violations.push(`statement coverage is ${accounting.coverage_percent}%`);
  }

  assert.deepEqual(violations, [], `${scenarioName} launch-contract violations:\n- ${violations.join('\n- ')}`);
  return { scenario: scenarioName, verifiedCount: verified.length, mustKeys: [...mustKeys] };
}

module.exports = { validateLaunchContract };
