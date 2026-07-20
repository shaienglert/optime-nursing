const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require(path.join(repoRoot, 'scripts', 'run_dynamic_persona_simulation_audit.cjs'));
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function loadJson(filePath) {
  if (!fs.existsSync(filePath)) return {};
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function sha256ForFile(filePath) {
  if (!fs.existsSync(filePath)) return '';
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function buildGovernanceContext(backendFacilities) {
  const registryPath = path.join(repoRoot, 'database', 'professional_rule_registry.json');
  const threeLayerPath = path.join(repoRoot, 'database', 'three_layer_decision_model_schema.json');
  const candidatePolicyPath = path.join(repoRoot, 'database', 'candidate_governance_policy.json');
  const evidencePath = path.join(repoRoot, 'database', 'facility_evidence_matrix_snapshot.json');
  const canonicalPath = path.join(repoRoot, 'database', 'florida_senior_living_inventory.json');

  const registry = loadJson(registryPath);
  const threeLayer = loadJson(threeLayerPath);
  const candidatePolicy = loadJson(candidatePolicyPath);
  const evidence = loadJson(evidencePath);
  const canonical = loadJson(canonicalPath);

  const canonicalByCms = new Map();
  (canonical.records || []).forEach((row, index) => {
    const cms = String(row.cms_certification_number || '').trim();
    if (cms) canonicalByCms.set(cms, index + 1);
  });

  const reconciliation = backendFacilities.map((facility) => {
    const cmsId = String(facility.cms_id || '').trim();
    const canonicalId = canonicalByCms.get(cmsId) || null;
    return {
      runtime_facility_id: facility.id,
      canonical_facility_id: canonicalId,
      cms_certification_number: cmsId || null,
      identity_status: canonicalId ? 'CONFIRMED_CANONICAL_ID' : 'UNRESOLVED_IDENTITY',
      source_provenance: canonicalId ? ['CMS Provider Information', 'Medicare Care Compare'] : ['runtime_db_only'],
    };
  });

  const unknownConfidence = backendFacilities.filter((facility) => {
    const raw = String(facility.confidence_level || '').toUpperCase();
    return !['HIGH', 'MEDIUM', 'LOW'].includes(raw);
  }).length;

  return {
    generated_at_utc: new Date().toISOString(),
    professional_rule_registry: {
      version: registry.phase || null,
      rule_count: (registry.rules || []).length,
      hash: sha256ForFile(registryPath),
      rules: registry.rules || [],
      validator_policy: registry.validator_policy || {},
      authority_model: registry.authority_model || {},
    },
    three_layer_model: {
      hash: sha256ForFile(threeLayerPath),
      allowed_classifications: threeLayer.allowed_classifications || [],
      governance_boundaries: threeLayer.governance_boundaries || {},
    },
    candidate_governance: {
      hash: sha256ForFile(candidatePolicyPath),
      candidate_lifecycle: candidatePolicy.candidate_lifecycle || [],
      hard_rejection_taxonomy: candidatePolicy.hard_rejection_taxonomy || [],
      governance_rules: candidatePolicy.governance_rules || [],
    },
    facility_evidence_runtime: {
      hash: sha256ForFile(evidencePath),
      verification_status_counts: evidence.verification_status_counts || {},
      source_level_counts: evidence.source_level_counts || {},
      unknown_field_counts: evidence.unknown_field_counts || {},
      policies: evidence.policies || { unknown_is_not_no: true, conflict_requires_review: true },
    },
    canonical_runtime_coverage: {
      canonical_total: canonical.record_count || 0,
      runtime_total: backendFacilities.length,
      confirmed_canonical_identity: reconciliation.filter((row) => row.identity_status === 'CONFIRMED_CANONICAL_ID').length,
      unresolved_identity: reconciliation.filter((row) => row.identity_status === 'UNRESOLVED_IDENTITY').length,
      reconciliation,
    },
    confidence_status: {
      total_evaluated: backendFacilities.length,
      known_confidence: backendFacilities.length - unknownConfidence,
      unknown_confidence: unknownConfidence,
      reason_breakdown: unknownConfidence > 0 ? { insufficient_evidence_provenance: unknownConfidence } : {},
    },
    validation_truth: {
      external_professional_validation: 'PARTIAL',
      benchmark_52_status: 'FAIL',
    },
  };
}

function postStrokeState() {
  const base = simulationHelpers.emptyState();
  return {
    ...base,
    relationship: 'Parent',
    gender: 'Male',
    ageGroup: '80-84',
    assistanceLevel: 'Skilled nursing care',
    budget: 0,
    futureCarePreference: 'Full continuum of care on one campus',
    notes: [
      'Age 80.',
      'Post-stroke recovery.',
      'Requires 24/7 nursing availability.',
      'Requires rehabilitation capability.',
      'Requires medication management.',
      'Mobility limitations and walker support needed.',
      'Family prefers Miami-Dade or nearby.',
      'Social engagement desirable.',
      'Budget unknown.',
    ].join(' '),
    referenceLocationType: 'County',
    referenceLocationValue: 'Miami-Dade County',
    happinessPreferences: ['Social activities'],
    humanIntelligenceV2: {
      ...base.humanIntelligenceV2,
      transitionRiskProfile: {
        ...base.humanIntelligenceV2.transitionRiskProfile,
        recentHospitalization: 'Yes',
        postHospitalRehabNeed: 'Yes',
      },
      distanceProfile: {
        ...base.humanIntelligenceV2.distanceProfile,
        driveTimes: { normal: '25', rushHour: '40', emergency: '20' },
      },
    },
  };
}

function ageOnlyState() {
  const base = simulationHelpers.emptyState();
  return {
    ...base,
    ageGroup: '80-84',
    assistanceLevel: 'Fully independent',
    notes: 'Age 80, no explicit nursing requirement provided.',
  };
}

function socialOnlyState() {
  const base = simulationHelpers.emptyState();
  return {
    ...base,
    assistanceLevel: 'Fully independent',
    happinessPreferences: ['Social activities'],
    notes: 'Prefers social activities.',
  };
}

function unknownBudgetState() {
  const base = simulationHelpers.emptyState();
  return {
    ...base,
    assistanceLevel: 'Some daily support',
    budget: 0,
    notes: 'Budget unknown and not mandatory.',
  };
}

function runWithState(facilities, governanceContext, state) {
  return runOptimeV2Engine(facilities, state, { mode: 'production', governanceContext });
}

function hasMustLabel(output, keyword) {
  const top = output.displayedRecommendations[0];
  if (!top) return false;
  const rows = top.report.audit.governedRequirements || [];
  return rows.some((row) => row.classification === 'MUST' && String(row.label || '').toLowerCase().includes(keyword));
}

function gatherTop5(output) {
  return output.displayedRecommendations.slice(0, 5).map((item, index) => {
    const governed = item.report.audit.governedFacilityDecision;
    return {
      rank: index + 1,
      facility: item.facility.name,
      canonical_id: governed?.canonical_facility_id || null,
      must_satisfied: governed?.must_satisfied || [],
      must_failed: governed?.must_failed || [],
      must_unknown: governed?.must_unknown || [],
      our_recommendation_alignment: (governed?.ranking_factors || []).find((row) => row.factor === 'OUR_RECOMMENDATION alignment')?.contribution || 0,
      nice_to_have_alignment: (governed?.ranking_factors || []).find((row) => row.factor === 'NICE_TO_HAVE alignment')?.contribution || 0,
      evidence_gaps: governed?.verification_required || [],
      sources: governed?.source_traceability || [],
      ranking_explanation: item.rankReason,
    };
  });
}

function main() {
  const backendFacilities = simulationHelpers.loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));
  const governanceContext = buildGovernanceContext(backendFacilities);

  const output = runWithState(facilities, governanceContext, postStrokeState());
  const top = output.displayedRecommendations[0];

  const errors = [];

  if (!output.governedRuntime.registry_consumed) errors.push('registry_not_consumed');
  if (!top?.report.audit.governedRequirements?.length) errors.push('three_layer_classification_absent');

  const allReqs = top?.report.audit.governedRequirements || [];
  const mustRows = allReqs.filter((row) => row.classification === 'MUST');
  const mustLabels = mustRows.map((row) => String(row.label).toLowerCase());
  if (!mustLabels.some((label) => label.includes('nursing'))) errors.push('explicit_nursing_must_lost');
  if (!mustLabels.some((label) => label.includes('rehabilitation') || label.includes('physical therapy'))) errors.push('explicit_rehab_must_lost');
  if (!mustLabels.some((label) => label.includes('medication'))) errors.push('explicit_medication_must_lost');

  const hasUnknownInMust = output.displayedRecommendations.some((item) => (item.report.audit.governedFacilityDecision?.must_unknown || []).length > 0);
  if (!hasUnknownInMust) errors.push('must_unknown_not_preserved');

  const mustFailedDisplayed = output.displayedRecommendations.some((item) => (item.report.audit.governedFacilityDecision?.must_failed || []).length > 0);
  if (mustFailedDisplayed) errors.push('must_failed_overridden_by_score');

  const evidenceMissing = output.displayedRecommendations.some((item) => !(item.report.audit.governedFacilityDecision?.evidence_records || []).length);
  if (evidenceMissing) errors.push('facility_evidence_layer_bypassed');

  const traceMissing = output.displayedRecommendations.some((item) => !(item.report.audit.governedFacilityDecision?.source_traceability || []).length);
  if (traceMissing) errors.push('traceability_missing');

  const unvalidatedMust = output.displayedRecommendations.some((item) =>
    (item.report.audit.governedRequirements || []).some((row) => row.classification === 'MUST' && row.origin === 'PROFESSIONAL_RULE_PENDING_VALIDATION'));
  if (unvalidatedMust) errors.push('unvalidated_rule_created_hard_must');

  const ageOnly = runWithState(facilities, governanceContext, ageOnlyState());
  if (hasMustLabel(ageOnly, '24/7') || hasMustLabel(ageOnly, 'nursing')) errors.push('negative_age_alone_created_nursing_must');

  const socialOnly = runWithState(facilities, governanceContext, socialOnlyState());
  if (hasMustLabel(socialOnly, 'social')) errors.push('negative_social_preference_became_must');

  const unknownBudget = runWithState(facilities, governanceContext, unknownBudgetState());
  const budgetForced = unknownBudget.rejected.some((item) => item.hardRejectionReasons.some((reason) => reason.toLowerCase().includes('budget') && reason.toLowerCase().includes('mandatory')));
  if (budgetForced) errors.push('negative_unknown_budget_became_strict_budget');

  const heuristicEvidenceHigh = output.displayedRecommendations.some((item) =>
    (item.report.audit.governedFacilityDecision?.evidence_records || []).some((row) => row.source_type === 'HEURISTIC_INFERRED' && row.confidence === 'HIGH'));
  if (heuristicEvidenceHigh) errors.push('missing_source_became_verified_evidence');

  const mustFailedRejected = output.rejected.filter((item) => (item.report.audit.governedFacilityDecision?.must_failed || []).length > 0).map((item) => item.facility.id);
  const displayedIds = new Set(output.displayedRecommendations.map((item) => item.facility.id));
  const overlap = mustFailedRejected.some((id) => displayedIds.has(id));
  if (overlap) errors.push('legacy_weight_overrode_verified_must');

  const resultsPageText = fs.readFileSync(path.join(repoRoot, 'frontend', 'src', 'app', 'results', 'results-page-client.tsx'), 'utf8');
  if (!resultsPageText.includes('engineOutput.displayedRecommendations') || !resultsPageText.includes('slice(0, TOP_RECOMMENDATION_COUNT)')) {
    errors.push('frontend_top5_not_connected_to_governed_runtime');
  }

  const top5 = gatherTop5(output);
  const top3Reqs = {
    MUST: mustRows.map((row) => ({ requirement_id: row.requirement_id, label: row.label, origin: row.origin })),
    OUR_RECOMMENDATION: allReqs.filter((row) => row.classification === 'OUR_RECOMMENDATION').map((row) => ({ requirement_id: row.requirement_id, label: row.label, origin: row.origin })),
    NICE_TO_HAVE: allReqs.filter((row) => row.classification === 'NICE_TO_HAVE').map((row) => ({ requirement_id: row.requirement_id, label: row.label, origin: row.origin })),
  };

  const outputPayload = {
    case_id: 'POST_STROKE_MIAMI_001',
    normalized_profile: {
      age_group: '80-84',
      care_context: 'post-stroke',
      explicit_needs: ['24/7 nursing availability', 'rehabilitation capability', 'medication management', 'mobility limitations'],
      preferences: ['Miami-Dade or nearby', 'social engagement desirable'],
      budget_status: 'UNKNOWN',
    },
    requirement_layers: top3Reqs,
    candidate_counts_by_stage: output.candidateStageCounts,
    top_5: top5,
  };

  const validationPayload = {
    status: errors.length === 0 ? 'PASS' : 'FAIL',
    errors,
    summary: {
      accepted: output.accepted.length,
      rejected: output.rejected.length,
      displayed: output.displayedRecommendations.length,
      top5_count: top5.length,
      registry_consumed: output.governedRuntime.registry_consumed,
    },
    negative_tests: {
      age_alone_no_nursing_must: !errors.includes('negative_age_alone_created_nursing_must'),
      social_preference_not_must: !errors.includes('negative_social_preference_became_must'),
      unknown_budget_preserved: !errors.includes('negative_unknown_budget_became_strict_budget'),
      unknown_capability_not_yes: !errors.includes('must_unknown_not_preserved'),
      score_cannot_override_must_failed: !errors.includes('must_failed_overridden_by_score'),
      unvalidated_rule_no_hard_must: !errors.includes('unvalidated_rule_created_hard_must'),
      legacy_weight_not_override_must: !errors.includes('legacy_weight_overrode_verified_must'),
      missing_source_not_verified: !errors.includes('missing_source_became_verified_evidence'),
    },
  };

  fs.writeFileSync(path.join(repoRoot, 'reports', 'POST_STROKE_MIAMI_001_RUNTIME_OUTPUT.json'), JSON.stringify(outputPayload, null, 2));
  fs.writeFileSync(path.join(repoRoot, 'reports', 'GOVERNED_RUNTIME_INTEGRATION_VALIDATION.json'), JSON.stringify(validationPayload, null, 2));

  console.log(`STATUS=${validationPayload.status}`);
  console.log(`TOP5=${top5.length}`);
  console.log(`ERRORS=${errors.length}`);

  if (errors.length > 0) {
    process.exitCode = 1;
  }
}

main();
