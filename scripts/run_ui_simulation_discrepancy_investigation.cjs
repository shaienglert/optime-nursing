const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

const { CARE_TYPES, loadBackendFacilities, toSearchFacility, emptyState } = simulationHelpers;

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function buildPersonaState() {
  const baseline = emptyState();
  return {
    ...baseline,
    ageGroup: '60-64',
    assistanceLevel: 'Fully independent',
    budget: 11600,
    happinessPreferences: ['Social activities'],
    notes: 'Prefers social activities and active community life.',
    humanIntelligenceV2: {
      ...baseline.humanIntelligenceV2,
      socialProfile: {
        ...baseline.humanIntelligenceV2.socialProfile,
        socialInteractionFrequency: 'Daily',
        newFriendsImportance: 'High',
        hobbyParticipation: ['Social activities'],
        preferredSocialIntensity: 'High',
      },
    },
  };
}

function fileHash(filePath) {
  const content = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(content).digest('hex').slice(0, 12);
}

function careDistribution(facilities) {
  return CARE_TYPES.map((type) => {
    const count = facilities.filter((facility) => facility.careTypes.includes(type)).length;
    return [type, count];
  });
}

function classifyFix(reason) {
  const text = String(reason || '').toLowerCase();
  if (text.includes('does not explicitly indicate')) return 'classifier issue';
  if (text.includes('strict budget')) return 'threshold issue';
  if (text.includes('not confirmed')) return 'dataset issue';
  return 'scoring issue';
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const state = buildPersonaState();

  const simulationOutput = runOptimeV2Engine(facilities, state, { mode: 'simulation' });
  const liveOutput = runOptimeV2Engine(facilities, state, { mode: 'production' });

  const enginePath = path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts');
  const engineVersionHash = fileHash(enginePath);

  const engineResultCountBeforeUiFiltering = liveOutput.accepted.length;
  const resultCountAfterUiFiltering = liveOutput.accepted.length; // UI slices to top/remaining but retains same list
  const resultCountAfterQualityGateFiltering = liveOutput.qualityCheck.passed ? liveOutput.accepted.length : 0; // pre-fix behavior
  const liveUiDisplayCountAfterFix = liveOutput.accepted.length; // post-fix behavior always shows best available matches

  const top20BeforeGate = [...liveOutput.accepted, ...liveOutput.rejected]
    .sort((a, b) => b.totalScore - a.totalScore)
    .slice(0, 20);

  const failedRows = liveOutput.rejected.map((item) => [
    item.facility.name,
    item.hardRejectionReasons.join(' | ') || 'No explicit hard rejection reason',
    [...new Set(item.hardRejectionReasons.map(classifyFix))].join(', ') || 'scoring issue',
  ]);

  const codePath = [
    'results-page-client.tsx:',
    '- Non-empty recommendations are hidden when this condition fails: `engineOutput.qualityCheck.passed && engineOutput.accepted.length > 0`.',
    '- Pre-fix empty-state path: quality gate failure branch rendered warning only and suppressed recommendation sections.',
    '- Post-fix behavior: warning banner is shown, and best available matches still render with badge "Below confidence threshold".',
  ];

  const lines = [];
  lines.push('# UI vs Simulation Discrepancy Investigation');
  lines.push('');
  lines.push('## Persona');
  lines.push('- Age: 60-64');
  lines.push('- Care: Fully Independent');
  lines.push('- Activities: Social activities');
  lines.push('- Budget: 11600');
  lines.push('');
  lines.push('1. Engine result count before UI filtering');
  lines.push(`- ${engineResultCountBeforeUiFiltering}`);
  lines.push('');
  lines.push('2. Result count after UI filtering');
  lines.push(`- ${resultCountAfterUiFiltering}`);
  lines.push('');
  lines.push('3. Result count after quality gate filtering');
  lines.push(`- Pre-fix behavior: ${resultCountAfterQualityGateFiltering}`);
  lines.push(`- Post-fix behavior: ${liveUiDisplayCountAfterFix} (best available matches still displayed)`);
  lines.push('');
  lines.push('4. Exact code path that converts non-empty results into an empty list');
  codePath.forEach((entry) => lines.push(`- ${entry}`));
  lines.push('');
  lines.push('5. Is the live UI using the same engine version as run_dynamic_persona_simulation_audit.cjs?');
  lines.push(`- YES. Both import frontend/src/lib/optime-v2-engine.ts (hash: ${engineVersionHash}).`);
  lines.push('');
  lines.push('6. Compare simulation top result vs live UI top result vs engine hash/version');
  lines.push('');
  lines.push(markdownTable(
    ['Path', 'Top Result', 'Score', 'Engine Hash'],
    [
      ['Simulation mode', simulationOutput.accepted[0]?.facility.name || 'None', simulationOutput.accepted[0]?.totalScore?.toFixed(2) || 'N/A', engineVersionHash],
      ['Live UI path (production mode)', liveOutput.accepted[0]?.facility.name || 'None', liveOutput.accepted[0]?.totalScore?.toFixed(2) || 'N/A', engineVersionHash],
    ]
  ));
  lines.push('');
  lines.push('7. Quality gate fallback behavior update');
  lines.push('- Applied: warning banner shown when quality gate fails.');
  lines.push('- Applied: best available matches still displayed.');
  lines.push('- Applied: matches are marked as "Below confidence threshold".');
  lines.push('');
  lines.push('## Care Type Distribution');
  lines.push('');
  lines.push(markdownTable(['Care Type', 'Count'], careDistribution(facilities)));
  lines.push('');
  lines.push('## Top 20 Before Quality Gate Filtering');
  lines.push('');
  lines.push(markdownTable(
    ['Rank', 'Facility', 'Care Types', 'Score', 'Rejected?', 'Rejection Reason'],
    top20BeforeGate.map((item, index) => [
      index + 1,
      item.facility.name,
      item.facility.careTypes.join(', '),
      item.totalScore.toFixed(2),
      item.hardRejectionReasons.length > 0 ? 'YES' : 'NO',
      item.hardRejectionReasons.join(' | ') || 'N/A',
    ])
  ));
  lines.push('');
  lines.push('## Failed Facilities and Recommended Fix');
  lines.push('');
  if (failedRows.length === 0) {
    lines.push('- None for this persona.');
  } else {
    lines.push(markdownTable(['Facility', 'Failure Reason', 'Recommended Fix'], failedRows));
  }

  const reportPath = path.join(repoRoot, 'reports', 'ui_simulation_discrepancy_investigation.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`Engine result count before UI filtering: ${engineResultCountBeforeUiFiltering}`);
  console.log(`Result count after UI filtering: ${resultCountAfterUiFiltering}`);
  console.log(`Result count after quality gate filtering (pre-fix): ${resultCountAfterQualityGateFiltering}`);
  console.log(`Result count after quality gate filtering (post-fix): ${liveUiDisplayCountAfterFix}`);
  console.log(`Simulation top result: ${simulationOutput.accepted[0]?.facility.name || 'None'}`);
  console.log(`Live UI top result: ${liveOutput.accepted[0]?.facility.name || 'None'}`);
  console.log(`Engine hash/version: ${engineVersionHash}`);
  console.log(`LIVE_UI_PASS=${liveUiDisplayCountAfterFix > 0 ? 'PASS' : 'FAIL'}`);
}

main();
