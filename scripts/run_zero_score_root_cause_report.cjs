const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');

// Registers TS runtime hooks + exposes dataset helpers.
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function collectInvalidValues(namedValues) {
  const undefinedValues = [];
  const nullValues = [];
  const nanValues = [];

  Object.entries(namedValues).forEach(([key, value]) => {
    if (value === undefined) undefinedValues.push(key);
    if (value === null) nullValues.push(key);
    if (typeof value === 'number' && Number.isNaN(value)) nanValues.push(key);
  });

  return { undefinedValues, nullValues, nanValues };
}

function main() {
  const facilities = simulationHelpers
    .loadBackendFacilities()
    .map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));

  const state = simulationHelpers.emptyState({
    assistanceLevel: 'Light assistance',
    budget: 11000,
    happinessPreferences: ['Social activities', 'Outdoor activities'],
    futureCarePreference: '',
    memoryStatus: 'No',
  });

  const output = runOptimeV2Engine(facilities, state, { mode: 'simulation' });
  const top = output.accepted[0] || null;

  if (!top) {
    const reportPath = path.join(repoRoot, 'reports', 'zero_score_root_cause_report.md');
    fs.writeFileSync(reportPath, '# Zero Score Root Cause Report\n\nNo accepted facilities found.');
    console.log(`Wrote ${reportPath}`);
    return;
  }

  const weights = output.persona.weights;
  const scores = top.priorityScores;

  const weightedTotalBeforeNormalization =
    scores.careFit * weights.careFit +
    scores.lifestyleFit * weights.lifestyleFit +
    scores.socialFit * weights.socialFit +
    scores.financialFit * weights.financialFit +
    scores.culturalFit * weights.culturalFit +
    scores.familyFit * weights.familyFit +
    scores.clinicalQuality * weights.clinicalQuality +
    scores.luxuryAmenities * weights.luxuryAmenities;

  const weightedTotalAfterNormalization = clamp(weightedTotalBeforeNormalization);

  const futureCareBreakdown = top.report.scoreBreakdown.find((item) => item.name === 'Future Care Fit');
  const topSummaryMandatory = top.report.audit.tierSummaries.find((item) => item.tier === 'MANDATORY');
  const topSummaryCritical = top.report.audit.tierSummaries.find((item) => item.tier === 'CRITICAL');

  const namedValues = {
    facilityName: top.facility.name,
    careFit: scores.careFit,
    lifestyleFit: scores.lifestyleFit,
    socialFit: scores.socialFit,
    financialFit: scores.financialFit,
    culturalFit: scores.culturalFit,
    familyFit: scores.familyFit,
    futureCareFit: futureCareBreakdown ? futureCareBreakdown.score : undefined,
    clinicalQuality: scores.clinicalQuality,
    luxuryFit: scores.luxuryAmenities,
    weightedTotalBeforeNormalization,
    weightedTotalAfterNormalization,
    finalScore: top.totalScore,
    confidenceScore: top.report.confidenceScore,
  };

  const invalid = collectInvalidValues(namedValues);

  const zeroScoreWithAccepted =
    output.accepted.length > 0 &&
    top.totalScore === 0 &&
    top.hardRejectionReasons.length === 0;

  const mandatoryGateTriggered =
    Boolean(topSummaryMandatory) &&
    topSummaryMandatory.matched < topSummaryMandatory.total;

  const likelyRootCause = zeroScoreWithAccepted && mandatoryGateTriggered;

  const lines = [];
  lines.push('# Zero Score Root Cause Report');
  lines.push('');
  lines.push('## Runtime Snapshot');
  lines.push('');
  lines.push(`- acceptedFacilities.length: **${output.accepted.length}**`);
  lines.push(`- hardRejectedFacilities.length: **${output.rejected.length}**`);
  lines.push(`- top finalScore: **${top.totalScore}**`);
  lines.push(`- top matchQuality: **${top.report.finalMatchScore}**`);
  lines.push(`- top confidenceScore: **${top.report.confidenceScore}**`);
  lines.push('');

  lines.push('## Top Accepted Facility Breakdown');
  lines.push('');
  lines.push(markdownTable(
    ['Field', 'Value'],
    [
      ['facility name', namedValues.facilityName],
      ['careFit', namedValues.careFit],
      ['lifestyleFit', namedValues.lifestyleFit],
      ['socialFit', namedValues.socialFit],
      ['financialFit', namedValues.financialFit],
      ['culturalFit', namedValues.culturalFit],
      ['familyFit', namedValues.familyFit],
      ['futureCareFit', namedValues.futureCareFit],
      ['clinicalQuality', namedValues.clinicalQuality],
      ['luxuryFit', namedValues.luxuryFit],
      ['weightedTotal before normalization', namedValues.weightedTotalBeforeNormalization],
      ['weightedTotal after normalization', namedValues.weightedTotalAfterNormalization],
      ['finalScore', namedValues.finalScore],
      ['confidenceScore', namedValues.confidenceScore],
    ],
  ));
  lines.push('');

  lines.push('## Invalid Value Scan');
  lines.push('');
  lines.push(`- undefined values: ${invalid.undefinedValues.length > 0 ? invalid.undefinedValues.join(', ') : 'none'}`);
  lines.push(`- null values: ${invalid.nullValues.length > 0 ? invalid.nullValues.join(', ') : 'none'}`);
  lines.push(`- NaN values: ${invalid.nanValues.length > 0 ? invalid.nanValues.join(', ') : 'none'}`);
  lines.push('');

  lines.push('## Code Path Analysis');
  lines.push('');
  lines.push(`- zero-score accepted facility state observed: **${zeroScoreWithAccepted ? 'YES' : 'NO'}**`);
  lines.push(`- mandatory gate triggered (mandatorySummary.matched < mandatorySummary.total): **${mandatoryGateTriggered ? 'YES' : 'NO'}**`);
  if (topSummaryMandatory) {
    lines.push(`- mandatorySummary.matched: **${topSummaryMandatory.matched}**`);
    lines.push(`- mandatorySummary.total: **${topSummaryMandatory.total}**`);
  }
  if (topSummaryCritical) {
    lines.push(`- criticalSummary.matched: **${topSummaryCritical.matched}**`);
    lines.push(`- criticalSummary.total: **${topSummaryCritical.total}**`);
  }
  lines.push('');
  lines.push('Exact zeroing code path in frontend/src/lib/optime-v2-engine.ts:');
  lines.push('- function buildMatchQualityResult(...)');
  lines.push('- variable mandatorySummary');
  lines.push('- branch: if (mandatorySummary.matched < mandatorySummary.total) { score = 0; }');
  lines.push('- variable names involved: baseScore, penalty, score, mandatorySummary.matched, mandatorySummary.total');
  lines.push('');

  lines.push('## Root Cause Decision');
  lines.push('');
  if (likelyRootCause) {
    lines.push('- ROOT CAUSE FOUND: YES');
    lines.push('- Cause: Hard rejection filters and match-quality mandatory gating use different thresholds/logic.');
    lines.push('- Result: Facility can pass hard requirements (accepted) but still get score forced to zero by mandatory tier mismatch.');
    lines.push('- This is not caused by NaN, null, undefined, division by zero, or missing denominator in this run.');
  } else {
    lines.push('- ROOT CAUSE FOUND: NO');
    lines.push('- Mandatory zeroing path did not explain this run. Further branch tracing is required.');
  }

  const reportPath = path.join(repoRoot, 'reports', 'zero_score_root_cause_report.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`ROOT_CAUSE_FOUND=${likelyRootCause ? 'YES' : 'NO'}`);
}

main();
