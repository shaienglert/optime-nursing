const path = require('path');
const fs = require('fs');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require(path.join(repoRoot, 'scripts', 'run_dynamic_persona_simulation_audit.cjs'));
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));
const { buildState: buildPostStrokeMiamiState } = require(path.join(repoRoot, 'benchmark', 'case_contracts', 'post_stroke_miami_001.cjs'));

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

function runTop10() {
  const backendFacilities = simulationHelpers.loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));
  const governanceContext = buildGovernanceContext(backendFacilities);
  const state = buildPostStrokeMiamiState(simulationHelpers.emptyState());
  const result = runOptimeV2Engine(facilities, state, { mode: 'production', governanceContext });
  const displayed = Array.isArray(result.displayedRecommendations) ? result.displayedRecommendations : [];

  const top10 = displayed.slice(0, 10).map((rec, index) => {
    const breakdown = rec.report.scoreBreakdown || [];
    const confidence = rec.report.audit?.confidence || {};
    const matchEvidence = rec.report.matchEvidenceStatus || {};
    const governed = rec.report.audit?.governedFacilityDecision || {};
    const checklist = rec.report.audit?.verificationChecklist || [];
    const yes = checklist.filter((item) => item.state === 'YES').length;
    const no = checklist.filter((item) => item.state === 'NO').length;
    const unknown = checklist.filter((item) => item.state === 'UNKNOWN' || item.state === 'LIMITED').length;

    return {
      rank: index + 1,
      facility_name: rec.facility.name,
      facility_id: rec.facility.id,
      canonical_facility_id: governed.canonical_facility_id || null,
      total_score: rec.totalScore,
      match_score: rec.report.finalMatchScore,
      proven_match_score: matchEvidence.provenMatchScore ?? rec.report.finalMatchScore,
      potential_match_score: matchEvidence.potentialMatchScore ?? null,
      potential_match_status: matchEvidence.potentialMatchStatus || 'REQUIRES_VERIFICATION',
      confidence_score: rec.report.confidenceScore,
      case_relevant_evidence_coverage_pct: matchEvidence.caseRelevantEvidenceCoveragePct ?? confidence.caseRelevantEvidenceCoveragePct ?? null,
      critical_evidence_coverage_pct: matchEvidence.criticalEvidenceCoveragePct ?? confidence.criticalEvidenceCoveragePct ?? null,
      evidence_confidence: matchEvidence.evidenceConfidence || confidence.evidenceCoverage || 'UNKNOWN',
      critical_unknowns: matchEvidence.criticalUnknowns || [],
      high_potential_needs_verification: Boolean(matchEvidence.highPotentialNeedsVerification),
      evidence_coverage: confidence.evidenceCoverage || 'UNKNOWN',
      comparison_confidence: confidence.comparisonConfidence || 'UNKNOWN',
      comparison_confidence_reason: confidence.comparisonConfidenceReason || '',
      verified_yes: yes,
      verified_no: no,
      unknown_count: unknown,
      governed_factors: governed.ranking_factors || [],
      score_breakdown: breakdown,
      must_satisfied: governed.must_satisfied || [],
      must_failed: governed.must_failed || [],
      must_unknown: governed.must_unknown || [],
      source_traceability: governed.source_traceability || [],
    };
  });

  const out = {
    generated_at_utc: new Date().toISOString(),
    total_displayed: displayed.length,
    top10,
  };
  process.stdout.write(JSON.stringify(out));
}

runTop10();
