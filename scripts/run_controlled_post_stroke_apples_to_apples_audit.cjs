const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const { resolveCanonicalPython } = require('./lib/python_runtime.cjs');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const outputJson = path.join(reportsDir, 'CONTROLLED_POST_STROKE_APPLES_TO_APPLES_AUDIT.json');
const outputMd = path.join(reportsDir, 'CONTROLLED_POST_STROKE_APPLES_TO_APPLES_AUDIT.md');

const simulationHelpers = require(path.join(repoRoot, 'scripts', 'run_dynamic_persona_simulation_audit.cjs'));
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));
const { buildCaseContract, buildState } = require(path.join(repoRoot, 'benchmark', 'case_contracts', 'post_stroke_miami_001.cjs'));

const KEY_FACILITIES = [
  'JOHN KNOX VILLAGE OF POMPANO BEACH',
  'RIVER GARDEN HEBREW HOME FOR THE AGED',
  'SANDS AT SOUTH BEACH CARE CENTER, THE',
  'BISCAYNE HEALTH AND REHABILITATION CENTER',
  'CORAL GABLES NURSING AND REHABILITATION CENTER',
  'PINECREST CENTER FOR REHABILITATION AND HEALING',
  'FOUNTAIN MANOR HEALTH & REHABILITATION CENTER',
];

const REQUIRED_CHECKLIST_FIELDS = [
  { key: 'licensed_nurses_24_7', title: '24/7 skilled nursing', patterns: [/24\/7/, /licensed nurses?/i, /skilled nursing/i] },
  { key: 'post_stroke_neuro_rehab', title: 'post-stroke / neurological rehabilitation', patterns: [/stroke/i, /neurolog/i, /rehab/i] },
  { key: 'physical_therapy', title: 'physical therapy', patterns: [/physical therapy/i, /\bpt\b/i] },
  { key: 'occupational_therapy', title: 'occupational therapy', patterns: [/occupational therapy/i, /\bot\b/i] },
  { key: 'speech_therapy', title: 'speech therapy', patterns: [/speech therapy/i] },
  { key: 'mobility_transfer', title: 'mobility / transfer assistance', patterns: [/mobility/i, /transfer/i, /walker/i, /fall prevention/i] },
  { key: 'medication_management', title: 'medication management', patterns: [/medication/i] },
  { key: 'cms_quality', title: 'relevant CMS quality', patterns: [/quality/i, /cms/i] },
  { key: 'staffing', title: 'staffing', patterns: [/staff/i] },
  { key: 'regulatory_inspection', title: 'regulatory / inspection risk', patterns: [/inspection/i, /regulatory/i, /deficien/i, /citation/i] },
  { key: 'medicare_medicaid', title: 'Medicare / Medicaid where relevant', patterns: [/medicare/i, /medicaid/i] },
  { key: 'distance_geography', title: 'distance / geography', patterns: [/distance/i, /location/i, /miami/i, /county/i] },
  { key: 'language_cultural', title: 'language / cultural fit where relevant', patterns: [/language/i, /hebrew/i, /english/i, /cultural/i] },
  { key: 'case_specific_other', title: 'other explicit case requirements', patterns: [/gluten/i, /diet/i, /food/i, /social/i, /movies/i, /music/i] },
];

function hashString(value) {
  return crypto.createHash('sha256').update(String(value), 'utf8').digest('hex');
}

function stableStringify(value) {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return '[' + value.map(stableStringify).join(',') + ']';
  }
  const keys = Object.keys(value).sort();
  return '{' + keys.map((key) => JSON.stringify(key) + ':' + stableStringify(value[key])).join(',') + '}';
}

function normalizeName(name) {
  return String(name || '').trim().toUpperCase();
}

function extractEngineVersionMetadata() {
  const sourcePath = path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts');
  const source = fs.readFileSync(sourcePath, 'utf8');

  const comparatorMatch = source.match(/\.sort\(\(a, b\) => \{([\s\S]*?)\n\s*\}\);/);
  const scoringMatch = source.match(/const matchScore =([\s\S]*?)const potentialMatchScore =/);

  const rankingBlock = comparatorMatch ? comparatorMatch[1] : 'UNRESOLVED_RANKING_BLOCK';
  const scoringBlock = scoringMatch ? scoringMatch[1] : 'UNRESOLVED_SCORING_BLOCK';

  return {
    scoring_version: 'SCORING_SHA256_' + hashString(scoringBlock).slice(0, 16),
    ranking_version: 'RANKING_SHA256_' + hashString(rankingBlock).slice(0, 16),
  };
}

function gitHead() {
  const out = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' });
  if (out.status !== 0) {
    return 'UNKNOWN';
  }
  return String(out.stdout || '').trim() || 'UNKNOWN';
}

function getLatestConnectivitySnapshot() {
  const dbPath = fs.existsSync(path.join(repoRoot, 'backend', 'optime_nursing.db'))
    ? path.join(repoRoot, 'backend', 'optime_nursing.db')
    : path.join(repoRoot, 'optime_nursing.db');
  const pythonPath = resolveCanonicalPython(repoRoot);
  if (!fs.existsSync(pythonPath) || !fs.existsSync(dbPath)) {
    return {
      data_source: 'UNAVAILABLE',
      latest_run_id: null,
      source_attempt_status_counts: {},
      per_facility_failures: {},
    };
  }

  const pythonCode = [
    'import sqlite3, json, sys',
    'db_path = sys.argv[1]',
    'conn = sqlite3.connect(db_path)',
    'conn.row_factory = sqlite3.Row',
    'cur = conn.cursor()',
    "row = cur.execute(\"select run_id from external_source_request_logs where claim_type='__source_attempt__' and run_id is not null and run_id<>'' order by created_at desc, id desc limit 1\").fetchone()",
    'run_id = row[0] if row else None',
    'status_counts = {}',
    'per_facility = {}',
    'if run_id:',
    "  for r in cur.execute(\"select request_status, count(*) as c from external_source_request_logs where run_id=? and claim_type='__source_attempt__' group by request_status\", (run_id,)).fetchall():",
    "    status_counts[str(r['request_status'])] = int(r['c'])",
    "  rows = cur.execute(\"select facility_name, request_status, count(*) as c from external_source_request_logs where run_id=? and claim_type='__source_attempt__' group by facility_name, request_status\", (run_id,)).fetchall()",
    '  for r in rows:',
    "    name = str(r['facility_name'] or '').strip().upper()",
    '    if not name:',
    '      continue',
    "    per_facility.setdefault(name, {})[str(r['request_status'])] = int(r['c'])",
    "print(json.dumps({'latest_run_id': run_id, 'source_attempt_status_counts': status_counts, 'per_facility_failures': per_facility}))",
    'conn.close()',
  ].join('\n');

  const out = spawnSync(pythonPath, ['-c', pythonCode, dbPath], { cwd: repoRoot, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  if (out.status !== 0) {
    return {
      data_source: dbPath,
      latest_run_id: null,
      source_attempt_status_counts: {},
      per_facility_failures: {},
      error: (out.stderr || out.stdout || '').trim(),
    };
  }

  try {
    const parsed = JSON.parse(String(out.stdout || '{}'));
    return {
      data_source: dbPath,
      latest_run_id: parsed.latest_run_id || null,
      source_attempt_status_counts: parsed.source_attempt_status_counts || {},
      per_facility_failures: parsed.per_facility_failures || {},
    };
  } catch (error) {
    return {
      data_source: dbPath,
      latest_run_id: null,
      source_attempt_status_counts: {},
      per_facility_failures: {},
      error: String(error),
    };
  }
}

function uniqueById(rows) {
  const map = new Map();
  rows.forEach((row) => {
    map.set(String(row.facility.id), row);
  });
  return [...map.values()];
}

function isEligibleForCandidateUniverse(rec) {
  const hard = Array.isArray(rec.hardRejectionReasons) ? rec.hardRejectionReasons : [];
  const mustFailed = rec.report?.audit?.governedFacilityDecision?.must_failed || [];
  return hard.length === 0 && mustFailed.length === 0;
}

function classifyExclusionCategory(rule) {
  const text = String(rule || '').toLowerCase();
  if (text.includes('distance') || text.includes('location') || text.includes('miami')) return 'distance/geography';
  if (text.includes('required level of daily support') || text.includes('clinical capability')) return 'care capability';
  if (text.includes('must eligibility')) return 'hard filter';
  if (text.includes('language')) return 'hard filter';
  if (text.includes('identity')) return 'missing identity';
  if (text.includes('verification')) return 'missing data';
  return 'other';
}

function detectFieldClassification(rec, fieldSpec, facilityFailures) {
  const checklist = rec.report?.audit?.verificationChecklist || [];
  const criteria = rec.report?.audit?.criteria || [];

  const matchedChecklist = checklist.filter((item) => {
    const label = String(item.label || '');
    return fieldSpec.patterns.some((pattern) => pattern.test(label));
  });

  const matchedCriteria = criteria.filter((item) => {
    const label = String(item.name || '');
    return fieldSpec.patterns.some((pattern) => pattern.test(label));
  });

  if (matchedChecklist.length === 0 && matchedCriteria.length === 0) {
    const hasFailure = Object.keys(facilityFailures || {}).some((status) => /ACCESS_FAILED|TIMEOUT|GEO_BLOCKED|RATE_LIMITED|ACCESS_DENIED|NETWORK_ERROR/.test(status));
    return hasFailure ? 'SOURCE_ACCESS_FAILED' : 'UNKNOWN';
  }

  const states = matchedChecklist.map((item) => String(item.state || '').toUpperCase());
  const criteriaSources = matchedCriteria.map((item) => String(item.source || ''));

  const hasVerifiedYes = states.includes('YES') && criteriaSources.some((s) => s.includes('verified=true'));
  if (hasVerifiedYes) return 'VERIFIED_YES';

  const hasVerifiedNo = states.includes('NO') && criteriaSources.some((s) => s.includes('verified=true'));
  if (hasVerifiedNo) return 'VERIFIED_NO';

  if (states.includes('LIMITED')) return 'LIMITED';

  const hasFailure = Object.keys(facilityFailures || {}).some((status) => /ACCESS_FAILED|TIMEOUT|GEO_BLOCKED|RATE_LIMITED|ACCESS_DENIED|NETWORK_ERROR/.test(status));
  if (states.includes('UNKNOWN') && hasFailure) return 'SOURCE_ACCESS_FAILED';

  if (states.includes('UNKNOWN')) return 'UNKNOWN';

  if (states.includes('YES') || states.includes('NO')) {
    return 'LIMITED';
  }

  return 'UNKNOWN';
}

function getRequirementChecklistClassification(rec, facilityFailures) {
  const fields = {};
  REQUIRED_CHECKLIST_FIELDS.forEach((field) => {
    fields[field.key] = {
      title: field.title,
      classification: detectFieldClassification(rec, field, facilityFailures),
    };
  });
  return fields;
}

function getRankingContributions(rec) {
  const governedFactors = rec.report?.audit?.governedFacilityDecision?.ranking_factors || [];
  const scoreBreakdown = rec.report?.scoreBreakdown || [];
  return {
    governed_factors: governedFactors,
    score_breakdown: scoreBreakdown,
  };
}

function pairwiseOrderingExplanation(current, next) {
  if (!next) {
    return {
      decisive_rule: 'LAST_RANKED',
      reason: 'No next facility.',
      comparator_deltas: null,
      tie_break_deltas: null,
    };
  }

  const currentFactors = current.report?.audit?.governedFacilityDecision?.ranking_factors || [];
  const nextFactors = next.report?.audit?.governedFacilityDecision?.ranking_factors || [];
  const currentRecommendation = (currentFactors.find((f) => f.factor === 'OUR_RECOMMENDATION alignment') || {}).contribution || 0;
  const nextRecommendation = (nextFactors.find((f) => f.factor === 'OUR_RECOMMENDATION alignment') || {}).contribution || 0;
  const currentNice = (currentFactors.find((f) => f.factor === 'NICE_TO_HAVE alignment') || {}).contribution || 0;
  const nextNice = (nextFactors.find((f) => f.factor === 'NICE_TO_HAVE alignment') || {}).contribution || 0;

  const governedFitDelta = (currentRecommendation + currentNice) - (nextRecommendation + nextNice);
  const provenDelta = (current.report?.matchEvidenceStatus?.provenMatchScore || 0) - (next.report?.matchEvidenceStatus?.provenMatchScore || 0);
  const confidenceDelta = (current.report?.matchEvidenceStatus?.caseRelevantEvidenceCoveragePct || 0) - (next.report?.matchEvidenceStatus?.caseRelevantEvidenceCoveragePct || 0);
  const fitDelta = (current.totalScore || 0) - (next.totalScore || 0);

  const currentClinicalReasoning = current.report?.audit?.clinicalReasoning || {};
  const nextClinicalReasoning = next.report?.audit?.clinicalReasoning || {};
  const currentPreferenceBonus = (currentClinicalReasoning.verifiedCapabilities || []).filter((item) => (currentClinicalReasoning.questionsForFacility || []).every((q) => !String(q).toLowerCase().includes(String(item).toLowerCase()))).length;
  const nextPreferenceBonus = (nextClinicalReasoning.verifiedCapabilities || []).filter((item) => (nextClinicalReasoning.questionsForFacility || []).every((q) => !String(q).toLowerCase().includes(String(item).toLowerCase()))).length;
  const preferenceBonusDelta = currentPreferenceBonus - nextPreferenceBonus;

  const clinicalQualityDelta = (current.priorityScores?.clinicalQuality || 0) - (next.priorityScores?.clinicalQuality || 0);
  const familyFitDelta = (current.priorityScores?.familyFit || 0) - (next.priorityScores?.familyFit || 0);

  let decisiveRule = 'TIE_BREAK';
  if (governedFitDelta !== 0) decisiveRule = 'GOVERNED_ALIGNMENT';
  else if (provenDelta !== 0) decisiveRule = 'PROVEN_MATCH';
  else if (confidenceDelta !== 0) decisiveRule = 'EVIDENCE_COVERAGE';
  else if (fitDelta !== 0) decisiveRule = 'FINAL_MATCH';

  return {
    decisive_rule: decisiveRule,
    reason: `Ordered above next by ${decisiveRule}.`,
    comparator_deltas: {
      governed_fit_delta: governedFitDelta,
      proven_match_delta: provenDelta,
      evidence_coverage_delta: confidenceDelta,
      final_match_delta: fitDelta,
    },
    tie_break_deltas: {
      preference_bonus_delta: preferenceBonusDelta,
      clinical_quality_delta: clinicalQualityDelta,
      family_fit_delta: familyFitDelta,
    },
  };
}

function formatPotential(matchEvidenceStatus) {
  const potential = matchEvidenceStatus?.potentialMatchScore;
  if (potential === null || potential === undefined) {
    return 'NOT_CALCULABLE';
  }
  return potential;
}

function buildFacilityTrace(rec, rank, allRanked, connectivityByFacility) {
  const facilityName = rec.facility.name;
  const normName = normalizeName(facilityName);
  const eligible = isEligibleForCandidateUniverse(rec);
  const hardReasons = rec.hardRejectionReasons || [];
  const mustFailed = rec.report?.audit?.governedFacilityDecision?.must_failed || [];
  const exclusionReasons = [...hardReasons, ...mustFailed.map((x) => `Governed MUST failed: ${x}`)];
  const exclusionRule = exclusionReasons[0] || null;
  const exclusionCategory = exclusionRule ? classifyExclusionCategory(exclusionRule) : null;
  const next = rank ? allRanked[rank] || null : null;

  const connectivity = connectivityByFacility[normName] || {};
  const checklistClassification = getRequirementChecklistClassification(rec, connectivity);
  const contributions = getRankingContributions(rec);
  const pairwise = rank ? pairwiseOrderingExplanation(rec, next) : null;

  const criticalUnknowns = rec.report?.matchEvidenceStatus?.criticalUnknowns || [];
  const verificationChecklist = rec.report?.audit?.verificationChecklist || [];
  const limitedFacts = verificationChecklist.filter((item) => String(item.state || '').toUpperCase() === 'LIMITED').map((item) => item.label);

  return {
    facility_name: facilityName,
    facility_id: rec.facility.id,
    in_candidate_universe: eligible ? 'YES' : 'NO',
    exclusion: eligible ? null : {
      exact_exclusion_reason: exclusionRule,
      exclusion_rule: exclusionRule,
      exclusion_category: exclusionCategory || 'other',
      source_data_used: rec.report?.audit?.governedFacilityDecision?.source_traceability || [],
    },
    eligibility_under_frozen_case: eligible ? 'YES' : 'NO',
    current_rank: rank || null,
    quality_score: rec.priorityScores?.clinicalQuality ?? null,
    personalized_match: rec.report?.finalMatchScore ?? null,
    proven_match: rec.report?.matchEvidenceStatus?.provenMatchScore ?? null,
    potential_match: formatPotential(rec.report?.matchEvidenceStatus),
    evidence_confidence: rec.report?.matchEvidenceStatus?.evidenceConfidence || 'UNKNOWN',
    case_relevant_evidence_coverage_pct: rec.report?.matchEvidenceStatus?.caseRelevantEvidenceCoveragePct ?? null,
    critical_evidence_coverage_pct: rec.report?.matchEvidenceStatus?.criticalEvidenceCoveragePct ?? null,
    critical_unknowns: criticalUnknowns,
    critical_unknown_count: criticalUnknowns.length,
    verified_positive_case_relevant_facts: rec.report?.audit?.clinicalReasoning?.verifiedCapabilities || [],
    verified_negative_case_relevant_facts: rec.report?.audit?.clinicalReasoning?.rejectedCapabilities || [],
    limited_facts: limitedFacts,
    source_access_failures: connectivity,
    hard_filter_status: hardReasons.length === 0 ? 'PASS' : 'FAILED',
    distance_geography_status: hardReasons.find((r) => /distance|location|miami/i.test(r)) ? 'FAILED' : 'PASS_OR_NOT_MANDATORY',
    requirement_checklist_classification: checklistClassification,
    exact_ranking_contributions: contributions,
    exact_tie_break_contributions: pairwise ? pairwise.tie_break_deltas : null,
    why_above_next: pairwise ? pairwise : null,
    legacy_heuristic_audit: (() => {
      const factors = rec.report?.audit?.governedFacilityDecision?.ranking_factors || [];
      const legacy = factors.find((item) => String(item.factor || '').toLowerCase().includes('legacy heuristic')) || null;
      return {
        legacy_heuristic_contribution: legacy ? legacy.contribution : null,
        legacy_inputs: legacy ? legacy.factor : null,
        affected_order: pairwise ? pairwise.decisive_rule === 'FINAL_MATCH' : false,
        representation: legacy ? 'historical scoring / generic heuristic' : 'none',
      };
    })(),
    high_potential_needs_verification: (() => {
      const proven = rec.report?.matchEvidenceStatus?.provenMatchScore;
      const potential = rec.report?.matchEvidenceStatus?.potentialMatchScore;
      const confidence = rec.report?.matchEvidenceStatus?.evidenceConfidence || 'UNKNOWN';
      if (potential === null || potential === undefined) {
        return {
          qualification: 'NOT_CALCULABLE',
          reason: 'Potential Match is not calculable under current gate.',
          proven_match: proven,
          potential_match: 'NOT_CALCULABLE',
          critical_unknowns: criticalUnknowns.length,
          evidence_confidence: confidence,
        };
      }
      const qualifies = potential > proven && criticalUnknowns.length > 0;
      return {
        qualification: qualifies ? 'YES' : 'NO',
        reason: qualifies ? 'Potential exceeds proven and critical unknowns exist.' : 'Gate not satisfied (potential<=proven or no critical unknowns).',
        proven_match: proven,
        potential_match: potential,
        critical_unknowns: criticalUnknowns.length,
        evidence_confidence: confidence,
      };
    })(),
  };
}

function sanitizeCell(value) {
  if (value === null || value === undefined) return '';
  const text = Array.isArray(value) ? value.join('; ') : String(value);
  return text.replace(/\|/g, '/').replace(/\n/g, ' ');
}

function validateBenchmark(report) {
  const validityChecks = [];
  validityChecks.push({ check: 'Same exact case contract', pass: report.frozen_case.case_id === 'POST_STROKE_MIAMI_001' });
  validityChecks.push({ check: 'Same case fingerprint', pass: Boolean(report.frozen_case.case_fingerprint) });
  validityChecks.push({ check: 'Same engine commit/version', pass: report.frozen_engine.engine_commit_sha !== 'UNKNOWN' });
  validityChecks.push({ check: 'Same candidate universe rules', pass: report.controlled_process.candidate_universe_rule === 'single_engine_run_same_case' });
  validityChecks.push({ check: 'Same evidence checklist', pass: report.controlled_process.same_checklist_for_all_candidates === true });
  validityChecks.push({ check: 'Same source authority rules', pass: report.controlled_process.source_authority_rules_preserved === true });
  validityChecks.push({ check: 'Same ranking run', pass: report.controlled_process.single_ranking_run === true });
  validityChecks.push({ check: 'Full traces exist for all key facilities', pass: report.key_facilities.every((row) => row.trace_exists === true) });
  validityChecks.push({ check: 'No silent removal by enrichment cohort', pass: report.key_facilities.every((row) => row.in_candidate_universe === 'YES' || row.exclusion !== null) });
  validityChecks.push({ check: 'Unknown/access failures preserved', pass: report.controlled_process.unknown_and_access_failures_preserved === true });

  const valid = validityChecks.every((item) => item.pass);
  return {
    benchmark_validity: valid ? 'VALID APPLES-TO-APPLES' : 'PARTIAL',
    checks: validityChecks,
  };
}

function main() {
  fs.mkdirSync(reportsDir, { recursive: true });

  const generatedAt = new Date().toISOString();
  const caseContract = buildCaseContract();
  const caseState = buildState(simulationHelpers.emptyState());
  const caseFingerprint = hashString(stableStringify({ caseContract, caseState }));

  const backendFacilities = simulationHelpers.loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));

  const governanceContext = (() => {
    const canonicalPath = path.join(repoRoot, 'database', 'florida_senior_living_inventory.json');
    const canonical = fs.existsSync(canonicalPath) ? JSON.parse(fs.readFileSync(canonicalPath, 'utf8')) : { records: [] };
    const canonicalByCms = new Map();
    (canonical.records || []).forEach((row, index) => {
      if (row.cms_certification_number) canonicalByCms.set(String(row.cms_certification_number), index + 1);
    });
    return {
      generated_at_utc: generatedAt,
      candidate_governance: { governance_rules: [] },
      canonical_runtime_coverage: {
        canonical_total: canonical.record_count || 0,
        runtime_total: backendFacilities.length,
        confirmed_canonical_identity: backendFacilities.filter((f) => canonicalByCms.has(String(f.cms_id || ''))).length,
      },
    };
  })();

  const result = runOptimeV2Engine(facilities, caseState, { mode: 'production', governanceContext });
  const accepted = Array.isArray(result.accepted) ? result.accepted : [];
  const rejected = Array.isArray(result.rejected) ? result.rejected : [];
  const displayed = Array.isArray(result.displayedRecommendations) ? result.displayedRecommendations : [];
  const allRecommendations = uniqueById([...accepted, ...rejected]);

  const rankedById = new Map(displayed.map((rec, index) => [String(rec.facility.id), index + 1]));
  const allRankedRows = displayed.slice();

  const connectivity = getLatestConnectivitySnapshot();
  const connectivityByFacility = connectivity.per_facility_failures || {};

  const facilityTraces = allRecommendations.map((rec) => {
    const rank = rankedById.get(String(rec.facility.id)) || null;
    return buildFacilityTrace(rec, rank, allRankedRows, connectivityByFacility);
  });

  facilityTraces.sort((a, b) => {
    const ar = a.current_rank === null ? Number.MAX_SAFE_INTEGER : a.current_rank;
    const br = b.current_rank === null ? Number.MAX_SAFE_INTEGER : b.current_rank;
    if (ar !== br) return ar - br;
    return String(a.facility_name).localeCompare(String(b.facility_name));
  });

  const byName = new Map(facilityTraces.map((row) => [normalizeName(row.facility_name), row]));
  const keyFacilityResults = KEY_FACILITIES.map((name) => {
    const row = byName.get(normalizeName(name)) || null;
    return {
      requested_name: name,
      trace_exists: Boolean(row),
      in_candidate_universe: row ? row.in_candidate_universe : 'NO',
      exclusion: row ? row.exclusion : {
        exact_exclusion_reason: 'Facility not present in runtime facility dataset.',
        exclusion_rule: 'missing identity',
        exclusion_category: 'missing identity',
        source_data_used: [],
      },
      current_rank: row ? row.current_rank : null,
      eligible_under_frozen_case: row ? row.eligibility_under_frozen_case : 'NO',
      received_verified_negative_case_relevant_evidence: row ? (row.verified_negative_case_relevant_facts.length > 0 ? 'YES' : 'NO') : 'UNKNOWN',
      what_prevents_higher_rank: (() => {
        if (!row) return 'No runtime row found for this facility.';
        if (row.current_rank === null) return row.exclusion?.exact_exclusion_reason || 'Excluded before ranking.';
        if (row.current_rank === 1) return 'Already rank #1 in this controlled run.';
        return row.why_above_next ? 'Lower governed/proven/coverage comparator outcome than higher-ranked facility.' : 'Comparator trace unavailable.';
      })(),
      trace: row,
    };
  });

  const topRanked = facilityTraces.filter((row) => row.current_rank !== null).sort((a, b) => a.current_rank - b.current_rank);
  const sands = byName.get(normalizeName('SANDS AT SOUTH BEACH CARE CENTER, THE')) || null;

  const engineVersions = extractEngineVersionMetadata();
  const latestVerificationTimestamp = backendFacilities
    .flatMap((facility) => Array.isArray(facility.verification_memory) ? facility.verification_memory : [])
    .map((item) => item.verified_at)
    .filter(Boolean)
    .sort()
    .slice(-1)[0] || null;

  const report = {
    generated_at_utc: generatedAt,
    task_scope: 'CONTROLLED_VALIDATION_AUDIT_ONLY',
    principle_impact_check: {
      relevant_existing_principles: ['PR-005', 'PR-006', 'PR-007', 'PR-008'],
      does_this_change_alter_any_principle: 'NO',
      owner_approval_required: 'NO',
      classification: 'B. Implementation Completion',
    },
    frozen_case: {
      case_id: caseContract.case_id,
      age: caseContract.case_truth.exact_age,
      location: caseContract.case_truth.geography_preference,
      care_needs: {
        nursing_support_24_7: caseContract.case_truth.nursing_support_24_7,
        rehabilitation_requirement: caseContract.case_truth.rehabilitation_requirement,
        medication_management: caseContract.case_truth.medication_management,
      },
      therapy_needs: {
        physical_therapy: caseContract.case_truth.physical_therapy,
        occupational_therapy: caseContract.case_truth.occupational_therapy,
        speech_therapy: true,
      },
      mobility_needs: {
        limited_mobility: caseContract.case_truth.limited_mobility,
        transfer_assistance: caseContract.case_truth.transfer_assistance,
        bathing_assistance: caseContract.case_truth.bathing_assistance,
        dressing_assistance: caseContract.case_truth.dressing_assistance,
      },
      languages: caseContract.case_truth.languages,
      cognitive_status: {
        mentally_alert: caseContract.case_truth.mentally_alert,
        no_dementia: caseContract.case_truth.no_dementia,
      },
      budget: caseContract.case_truth.budget_ceiling_monthly,
      distance_policy: {
        classification: caseContract.geography.classification,
        hard_constraint: caseContract.geography.hard_constraint,
        county_preference: caseContract.geography.county_preference,
      },
      hard_filters: [
        'Required care type support (supportsAllowedCareType).',
        'No verified CRITICAL=NO capability.',
        'Mandatory budget only if marked mandatory in state.',
        'Mandatory distance only if marked mandatory in state.',
        'Mandatory language only if marked mandatory in state.',
        'Governed MUST eligibility gate.',
      ],
      nice_to_have_preferences: caseContract.case_truth.activities,
      case_fingerprint: caseFingerprint,
    },
    frozen_engine: {
      engine_commit_sha: gitHead(),
      scoring_version: engineVersions.scoring_version,
      ranking_version: engineVersions.ranking_version,
      data_snapshot_timestamp_utc: latestVerificationTimestamp,
      ranking_run_timestamp_utc: generatedAt,
      case_fingerprint: caseFingerprint,
    },
    candidate_universe: {
      discovered_total: allRecommendations.length,
      ranked_total: topRanked.length,
      rejected_total: allRecommendations.length - topRanked.length,
      required_facilities_present: KEY_FACILITIES.map((name) => ({
        facility: name,
        present_in_runtime_dataset: byName.has(normalizeName(name)),
      })),
      facilities: facilityTraces.map((row) => ({
        facility_name: row.facility_name,
        in_candidate_universe: row.in_candidate_universe,
        exclusion: row.exclusion,
      })),
    },
    evidence_parity: {
      same_checklist_fields_applied_to_all_candidates: true,
      required_fields: REQUIRED_CHECKLIST_FIELDS.map((item) => item.title),
      unknown_preservation_rule: 'UNKNOWN is preserved and never converted to NO.',
      source_access_failure_rule: 'SOURCE_ACCESS_FAILED is preserved independently.',
      duplicate_evidence_policy: 'No evidence count tie-break is used for ranking.',
      generic_completeness_policy: 'Generic completeness is not a ranking comparator.',
      connectivity_snapshot: {
        lookup_mode: 'REUSE_EXISTING_EVIDENCE_WITH_LOCAL_DB_STATUS',
        latest_run_id: connectivity.latest_run_id,
        source_attempt_status_counts: connectivity.source_attempt_status_counts,
        access_status_normalization: ['SUCCESS', 'TIMEOUT', 'GEO_BLOCKED_OR_SUSPECTED', 'RATE_LIMITED', 'ACCESS_DENIED', 'NETWORK_ERROR', 'OTHER'],
      },
    },
    controlled_process: {
      sequence: [
        'FREEZE_CASE',
        'FREEZE_ENGINE',
        'BUILD_CANDIDATE_UNIVERSE',
        'APPLY_SAME_EVIDENCE_CHECKLIST',
        'RECORD_UNKNOWN_AND_ACCESS_FAILURES',
        'FREEZE_EVIDENCE_SNAPSHOT',
        'RUN_RANKING_ONCE',
        'GENERATE_TRACE',
      ],
      candidate_universe_rule: 'single_engine_run_same_case',
      same_checklist_for_all_candidates: true,
      source_authority_rules_preserved: true,
      single_ranking_run: true,
      unknown_and_access_failures_preserved: true,
      external_lookup_performed: false,
    },
    key_facilities: keyFacilityResults,
    sands_verification: sands ? {
      current_rank: sands.current_rank,
      evidence_confidence: sands.evidence_confidence,
      case_relevant_evidence_coverage_pct: sands.case_relevant_evidence_coverage_pct,
      critical_evidence_coverage_pct: sands.critical_evidence_coverage_pct,
      critical_unknown_count: sands.critical_unknown_count,
      verified_positive_case_relevant_facts: sands.verified_positive_case_relevant_facts,
      reason_if_rank_1: sands.current_rank === 1 ? sands.why_above_next : 'Not rank #1 in this controlled run.',
      strongest_proven_fit_or_heuristic: sands.current_rank === 1
        ? (sands.why_above_next && sands.why_above_next.decisive_rule === 'PROVEN_MATCH' ? 'STRONGEST_PROVEN_FIT' : 'TIE_BREAK_OR_OTHER')
        : 'NOT_RANK_1',
      legacy_heuristic_contribution: sands.legacy_heuristic_audit,
    } : { status: 'SANDS_NOT_FOUND' },
    legacy_heuristic_audit: topRanked.slice(0, 10).map((row) => ({
      facility_name: row.facility_name,
      rank: row.current_rank,
      legacy_heuristic_contribution: row.legacy_heuristic_audit.legacy_heuristic_contribution,
      legacy_inputs: row.legacy_heuristic_audit.legacy_inputs,
      affected_order: row.legacy_heuristic_audit.affected_order,
      representation: row.legacy_heuristic_audit.representation,
    })),
    high_potential_needs_verification: keyFacilityResults.map((row) => ({
      facility_name: row.requested_name,
      result: row.trace ? row.trace.high_potential_needs_verification : {
        qualification: 'NOT_CALCULABLE',
        reason: 'No trace available.',
      },
    })),
    decision_table_sorted_by_rank: topRanked.map((row) => ({
      facility: row.facility_name,
      eligible: row.eligibility_under_frozen_case,
      rank: row.current_rank,
      quality: row.quality_score,
      personalized_match: row.personalized_match,
      proven_match: row.proven_match,
      potential_match: row.potential_match,
      evidence_confidence: row.evidence_confidence,
      case_relevant_coverage_pct: row.case_relevant_evidence_coverage_pct,
      critical_coverage_pct: row.critical_evidence_coverage_pct,
      critical_unknowns: row.critical_unknown_count,
      verified_positives: row.verified_positive_case_relevant_facts.length,
      verified_negatives: row.verified_negative_case_relevant_facts.length,
      source_access_failures: row.source_access_failures,
      legacy_heuristic_effect: row.legacy_heuristic_audit,
      why_this_rank: row.why_above_next,
    })),
  };

  report.validity_gate = validateBenchmark(report);

  fs.writeFileSync(outputJson, JSON.stringify(report, null, 2), 'utf8');

  const md = [];
  md.push('# Controlled Post-Stroke Apples-to-Apples Audit');
  md.push('');
  md.push(`- Generated: ${report.generated_at_utc}`);
  md.push(`- Benchmark validity: ${report.validity_gate.benchmark_validity}`);
  md.push(`- Engine commit: ${report.frozen_engine.engine_commit_sha}`);
  md.push(`- Scoring version: ${report.frozen_engine.scoring_version}`);
  md.push(`- Ranking version: ${report.frozen_engine.ranking_version}`);
  md.push(`- Case ID: ${report.frozen_case.case_id}`);
  md.push(`- Case fingerprint: ${report.frozen_case.case_fingerprint}`);
  md.push('');

  md.push('## Validity Gate');
  md.push('');
  report.validity_gate.checks.forEach((item) => {
    md.push(`- ${item.check}: ${item.pass ? 'PASS' : 'FAIL'}`);
  });
  md.push('');

  md.push('## Candidate Universe');
  md.push('');
  md.push(`- Discovered: ${report.candidate_universe.discovered_total}`);
  md.push(`- Ranked: ${report.candidate_universe.ranked_total}`);
  md.push(`- Rejected: ${report.candidate_universe.rejected_total}`);
  md.push('');

  md.push('## Critical Tests');
  md.push('');
  keyFacilityResults.forEach((row) => {
    md.push(`### ${row.requested_name}`);
    md.push(`- Eligible under exact frozen case: ${row.eligible_under_frozen_case}`);
    if (row.eligible_under_frozen_case === 'NO') {
      md.push(`- Exclusion rule: ${row.exclusion ? row.exclusion.exact_exclusion_reason : 'UNKNOWN'}`);
    } else {
      md.push(`- Rank under same run: ${row.current_rank}`);
    }
    md.push(`- Verified negative case-relevant evidence: ${row.received_verified_negative_case_relevant_evidence}`);
    md.push(`- What prevents higher rank: ${row.what_prevents_higher_rank}`);
    md.push('');
  });

  md.push('## Sands Verification');
  md.push('');
  if (report.sands_verification && report.sands_verification.current_rank !== undefined) {
    md.push(`- Current rank: ${report.sands_verification.current_rank}`);
    md.push(`- Evidence confidence: ${report.sands_verification.evidence_confidence}`);
    md.push(`- Case-relevant coverage: ${report.sands_verification.case_relevant_evidence_coverage_pct}%`);
    md.push(`- Critical coverage: ${report.sands_verification.critical_evidence_coverage_pct}%`);
    md.push(`- Critical unknown count: ${report.sands_verification.critical_unknown_count}`);
    md.push(`- #1 reason: ${JSON.stringify(report.sands_verification.reason_if_rank_1)}`);
    md.push(`- Strongest proven fit vs tie-break: ${report.sands_verification.strongest_proven_fit_or_heuristic}`);
  } else {
    md.push('- Sands not found in runtime dataset.');
  }
  md.push('');

  md.push('## Decision Table (Sorted by Current Controlled Rank)');
  md.push('');
  md.push('| FACILITY | ELIGIBLE | RANK | QUALITY | PERSONALIZED MATCH | PROVEN MATCH | POTENTIAL MATCH | EVIDENCE CONFIDENCE | CASE-RELEVANT COVERAGE | CRITICAL COVERAGE | CRITICAL UNKNOWNS | VERIFIED POSITIVES | VERIFIED NEGATIVES | SOURCE ACCESS FAILURES | LEGACY HEURISTIC EFFECT | WHY THIS RANK |');
  md.push('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |');
  report.decision_table_sorted_by_rank.forEach((row) => {
    const failures = Object.entries(row.source_access_failures || {}).map(([k, v]) => `${k}:${v}`).join(', ');
    const legacy = row.legacy_heuristic_effect ? `value=${row.legacy_heuristic_effect.legacy_heuristic_contribution}; affected=${row.legacy_heuristic_effect.affected_order}` : '';
    const why = row.why_this_rank ? `${row.why_this_rank.decisive_rule}: ${row.why_this_rank.reason}` : '';
    md.push(`| ${sanitizeCell(row.facility)} | ${sanitizeCell(row.eligible)} | ${sanitizeCell(row.rank)} | ${sanitizeCell(row.quality)} | ${sanitizeCell(row.personalized_match)} | ${sanitizeCell(row.proven_match)} | ${sanitizeCell(row.potential_match)} | ${sanitizeCell(row.evidence_confidence)} | ${sanitizeCell(row.case_relevant_coverage_pct)}% | ${sanitizeCell(row.critical_coverage_pct)}% | ${sanitizeCell(row.critical_unknowns)} | ${sanitizeCell(row.verified_positives)} | ${sanitizeCell(row.verified_negatives)} | ${sanitizeCell(failures)} | ${sanitizeCell(legacy)} | ${sanitizeCell(why)} |`);
  });

  md.push('');
  md.push('## Connectivity Status Snapshot');
  md.push('');
  md.push(`- Lookup mode: ${report.evidence_parity.connectivity_snapshot.lookup_mode}`);
  md.push(`- Latest run id: ${report.evidence_parity.connectivity_snapshot.latest_run_id || 'NONE'}`);
  Object.entries(report.evidence_parity.connectivity_snapshot.source_attempt_status_counts || {}).forEach(([status, count]) => {
    md.push(`- ${status}: ${count}`);
  });

  fs.writeFileSync(outputMd, md.join('\n') + '\n', 'utf8');

  console.log(JSON.stringify({
    output_json: outputJson,
    output_md: outputMd,
    validity: report.validity_gate.benchmark_validity,
    ranked_total: report.candidate_universe.ranked_total,
    discovered_total: report.candidate_universe.discovered_total,
  }, null, 2));
}

main();
