const path = require('path');
const fs = require('fs');

const repoRoot = path.join(__dirname, '..', '..');
const simulationHelpers = require(path.join(repoRoot, 'scripts', 'run_dynamic_persona_simulation_audit.cjs'));
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function loadJson(filePath) {
  if (!fs.existsSync(filePath)) return {};
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function buildGovernanceContext(backendFacilities) {
  const registry = loadJson(path.join(repoRoot, 'database', 'professional_rule_registry.json'));
  const threeLayer = loadJson(path.join(repoRoot, 'database', 'three_layer_decision_model_schema.json'));
  const candidatePolicy = loadJson(path.join(repoRoot, 'database', 'candidate_governance_policy.json'));
  const evidenceSnapshot = loadJson(path.join(repoRoot, 'database', 'facility_evidence_matrix_snapshot.json'));
  const canonical = loadJson(path.join(repoRoot, 'database', 'florida_senior_living_inventory.json'));

  const canonicalByCms = new Map();
  (canonical.records || []).forEach((row, index) => {
    if (row.cms_certification_number) {
      canonicalByCms.set(String(row.cms_certification_number), index + 1);
    }
  });

  const reconciliation = backendFacilities.map((facility) => {
    const canonicalId = canonicalByCms.get(String(facility.cms_id || '')) || null;
    return {
      runtime_facility_id: facility.id,
      canonical_facility_id: canonicalId,
      cms_certification_number: facility.cms_id || null,
      identity_status: canonicalId ? 'CONFIRMED_CANONICAL_ID' : 'UNRESOLVED_IDENTITY',
      source_provenance: canonicalId ? ['CMS Provider Information', 'Medicare Care Compare'] : ['runtime_db_only'],
    };
  });

  return {
    generated_at_utc: new Date().toISOString(),
    professional_rule_registry: {
      version: registry.phase || null,
      rule_count: (registry.rules || []).length,
      hash: '',
      rules: registry.rules || [],
      validator_policy: registry.validator_policy || {},
      authority_model: registry.authority_model || {},
    },
    three_layer_model: {
      hash: '',
      allowed_classifications: threeLayer.allowed_classifications || [],
      governance_boundaries: threeLayer.governance_boundaries || {},
    },
    candidate_governance: {
      hash: '',
      candidate_lifecycle: candidatePolicy.candidate_lifecycle || [],
      hard_rejection_taxonomy: candidatePolicy.hard_rejection_taxonomy || [],
      governance_rules: candidatePolicy.governance_rules || [],
    },
    facility_evidence_runtime: {
      hash: '',
      verification_status_counts: evidenceSnapshot.verification_status_counts || {},
      source_level_counts: evidenceSnapshot.source_level_counts || {},
      unknown_field_counts: evidenceSnapshot.unknown_field_counts || {},
      policies: evidenceSnapshot.policies || { unknown_is_not_no: true, conflict_requires_review: true },
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
      known_confidence: 0,
      unknown_confidence: backendFacilities.length,
      reason_breakdown: { benchmark_runtime_context: backendFacilities.length },
    },
    validation_truth: {
      external_professional_validation: 'PARTIAL',
      benchmark_52_status: 'FAIL',
    },
  };
}

function parseCasePayload(raw) {
  try {
    return JSON.parse(raw || '{}');
  } catch (error) {
    return {};
  }
}

function toState(casePayload) {
  const base = simulationHelpers.emptyState();
  const explicitNeeds = casePayload.explicit_needs || [];
  const nonNegotiables = casePayload.explicit_non_negotiables || [];
  const knownUnknowns = casePayload.known_unknowns || [];
  const location = casePayload.location || {};

  const notes = [
    ...(explicitNeeds || []),
    ...(nonNegotiables || []),
    ...(knownUnknowns || []).map((item) => `UNKNOWN: ${item}`),
    location.county ? `Preferred county ${location.county}` : '',
  ].filter(Boolean).join('. ');

  return {
    ...base,
    relationship: 'Parent',
    gender: casePayload.person_profile?.gender || 'Unknown',
    ageGroup: casePayload.person_profile?.age_group || '80-84',
    assistanceLevel: explicitNeeds.join(' ').toLowerCase().includes('24/7') ? 'Skilled nursing care' : 'Some daily support',
    futureCarePreference: 'Full continuum of care on one campus',
    budget: 7000,
    notes,
    referenceLocationType: location.county ? 'County' : 'Region',
    referenceLocationValue: location.county || location.region || 'South Florida',
    humanIntelligenceV2: {
      ...base.humanIntelligenceV2,
      transitionRiskProfile: {
        ...base.humanIntelligenceV2.transitionRiskProfile,
        recentHospitalization: explicitNeeds.join(' ').toLowerCase().includes('post-stroke') ? 'Yes' : 'Unknown',
        postHospitalRehabNeed: explicitNeeds.join(' ').toLowerCase().includes('rehab') ? 'Yes' : 'Unknown',
      },
    },
  };
}

function runCase(casePayload) {
  const backendFacilities = simulationHelpers.loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));
  const governanceContext = buildGovernanceContext(backendFacilities);
  const state = toState(casePayload);
  const result = runOptimeV2Engine(facilities, state, { mode: 'production', governanceContext });

  const top5 = result.displayedRecommendations.slice(0, 5).map((rec) => ({
    facility_name: rec.facility.name,
    location: [rec.facility.city, rec.facility.state].filter(Boolean).join(', '),
    why_selected: rec.shortExplanation,
    must_satisfied: rec.report.audit.clinicalReasoning.verifiedCapabilities || [],
    must_failed: rec.report.audit.clinicalReasoning.rejectedCapabilities || [],
    must_unknown: rec.report.audit.clinicalReasoning.unknownCapabilities || [],
    recommendation_alignment: rec.report.audit.clinicalReasoning.medicalMatch || '',
    nice_to_have_alignment: rec.report.audit.clinicalReasoning.lifestyleMatch || '',
    tradeoffs: [rec.report.audit.clinicalReasoning.futureCareMatch || ''],
    evidence_gaps: rec.report.audit.verificationRequest.items
      .filter((item) => item.state === 'UNKNOWN')
      .map((item) => item.label),
    sources: [],
    confidence: String(rec.report.audit.verificationRequest.confidenceScore || 'UNKNOWN'),
  }));

  return {
    run_status: 'OK',
    top_5: top5,
    accepted_count: result.acceptedRecommendations.length,
    rejected_count: result.rejectedRecommendations.length,
    fallback_count: result.bestAvailableRecommendations.length,
    chain_breaks: [],
  };
}

function main() {
  const payload = parseCasePayload(process.argv[2]);
  try {
    const out = runCase(payload);
    process.stdout.write(JSON.stringify(out));
  } catch (error) {
    process.stdout.write(JSON.stringify({
      run_status: 'CHAIN_BREAK',
      error: String(error?.message || error),
      chain_breaks: ['OPTIME runtime adapter failed to execute frontend engine path'],
      top_5: [],
    }));
    process.exitCode = 0;
  }
}

main();
