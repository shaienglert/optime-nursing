const fs = require('fs');
const path = require('path');

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

function recommendFix(reason) {
  const text = String(reason || '').toLowerCase();
  if (text.includes('does not explicitly indicate memory care') || text.includes('does not explicitly indicate skilled nursing')) {
    return 'classifier issue';
  }
  if (text.includes('strict budget requirement')) {
    return 'threshold issue';
  }
  if (text.includes('not confirmed')) {
    return 'dataset issue';
  }
  return 'scoring issue';
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

function careTypeDistribution(facilities) {
  return CARE_TYPES.map((type) => {
    const count = facilities.filter((facility) => facility.careTypes.includes(type)).length;
    const share = Math.round((count / Math.max(1, facilities.length)) * 100);
    return [type, count, `${share}%`];
  });
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const state = buildPersonaState();

  const result = runOptimeV2Engine(facilities, state, { mode: 'production' });
  const allRanked = [...result.accepted, ...result.rejected].sort((a, b) => b.totalScore - a.totalScore);

  const independentCount = facilities.filter((facility) => facility.careTypes.includes('Independent Living')).length;
  const activeAdultCount = facilities.filter((facility) => facility.careTypes.includes('Active Adult 55+')).length;
  const datasetLimitation = independentCount < 10;

  const top20Rows = allRanked.slice(0, 20).map((item, index) => [
    index + 1,
    item.facility.name,
    item.facility.careTypes.join(', '),
    item.totalScore.toFixed(2),
    item.hardRejectionReasons.length > 0 ? 'YES' : 'NO',
    item.hardRejectionReasons.length > 0 ? item.hardRejectionReasons.join(' | ') : 'N/A',
  ]);

  const failedRows = result.rejected.map((item) => {
    const reasons = item.hardRejectionReasons.length > 0 ? item.hardRejectionReasons : ['No explicit hard rejection reason'];
    const fixes = [...new Set(reasons.map(recommendFix))].join(', ');
    return [
      item.facility.name,
      item.facility.careTypes.join(', '),
      reasons.join(' | '),
      fixes,
    ];
  });

  const lines = [];
  lines.push('# Persona Quality-Gate Failure Investigation');
  lines.push('');
  lines.push('## Persona');
  lines.push('');
  lines.push('- Age: 60-64');
  lines.push('- Care level: Fully Independent');
  lines.push('- Budget: 11600');
  lines.push('- Preference: Social activities');
  lines.push('');
  lines.push('## Investigation Output');
  lines.push('');
  lines.push(`1. Total facilities evaluated: **${facilities.length}**`);
  lines.push('');
  lines.push('2. Care type distribution after taxonomy classification:');
  lines.push('');
  lines.push(markdownTable(['Care Type', 'Count', 'Share'], careTypeDistribution(facilities)));
  lines.push('');
  lines.push(`3. Number of Independent Living communities found: **${independentCount}**`);
  lines.push(`4. Number of Active Adult 55+ communities found: **${activeAdultCount}**`);
  lines.push('');
  if (datasetLimitation) {
    lines.push('**DATASET LIMITATION: Fewer than 10 Independent Living communities exist in candidate pool.**');
    lines.push('');
  }
  lines.push('5. Top 20 facilities before quality gate filtering:');
  lines.push('');
  lines.push(markdownTable(['Rank', 'Facility', 'Care Types', 'Score', 'Failed Gate?', 'Failure Reason'], top20Rows));
  lines.push('');
  lines.push('6. Exact reason each facility failed the quality gate:');
  lines.push('');
  if (failedRows.length === 0) {
    lines.push('No facilities failed hard requirement filtering for this persona.');
  } else {
    lines.push(markdownTable(['Facility', 'Care Types', 'Failure Reason', 'Recommended Fix Type'], failedRows));
  }
  lines.push('');
  lines.push('7. Recommended fix summary:');
  lines.push('');
  if (failedRows.length === 0) {
    lines.push('- No immediate classifier/dataset/threshold/scoring fix required for this persona.');
  } else {
    const fixCounts = { 'classifier issue': 0, 'dataset issue': 0, 'threshold issue': 0, 'scoring issue': 0 };
    failedRows.forEach((row) => {
      row[3].split(',').map((entry) => entry.trim()).forEach((fix) => {
        if (fixCounts[fix] !== undefined) fixCounts[fix] += 1;
      });
    });
    Object.entries(fixCounts).forEach(([fix, count]) => {
      lines.push(`- ${fix}: ${count}`);
    });
  }
  lines.push('');
  lines.push(`Quality Gate Status: **${result.qualityCheck.passed ? 'PASS' : 'FAIL'}**`);
  if (!result.qualityCheck.passed) {
    lines.push(`Quality Gate Failures: ${result.qualityCheck.failures.join(' | ')}`);
  }

  const reportPath = path.join(repoRoot, 'reports', 'persona_quality_gate_failure_investigation.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`Total facilities evaluated: ${facilities.length}`);
  console.log(`Independent Living count: ${independentCount}`);
  console.log(`Active Adult 55+ count: ${activeAdultCount}`);
  if (datasetLimitation) {
    console.log('DATASET LIMITATION');
  }
  console.log(`Persona quality gate: ${result.qualityCheck.passed ? 'PASS' : 'FAIL'}`);
}

main();
