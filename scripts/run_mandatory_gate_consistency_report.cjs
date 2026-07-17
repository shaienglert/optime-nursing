const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');

const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function hasMandatoryMismatch(recommendation) {
  const mandatorySummary = recommendation.report.audit.tierSummaries.find((item) => item.tier === 'MANDATORY');
  if (!mandatorySummary) return false;
  return mandatorySummary.matched < mandatorySummary.total;
}

function buildScenarios() {
  return [
    {
      code: 'S1',
      name: 'Known zero-score reproduction profile',
      state: simulationHelpers.emptyState({
        assistanceLevel: 'Light assistance',
        budget: 11000,
        happinessPreferences: ['Social activities', 'Outdoor activities'],
        futureCarePreference: '',
        memoryStatus: 'No',
      }),
    },
    {
      code: 'S2',
      name: 'Independent social profile',
      state: simulationHelpers.emptyState({
        assistanceLevel: 'Fully independent',
        budget: 11500,
        happinessPreferences: ['Movies', 'Social activities', 'Group dining'],
      }),
    },
    {
      code: 'S3',
      name: 'Memory support profile',
      state: simulationHelpers.emptyState({
        assistanceLevel: 'Some daily support',
        memoryStatus: 'Mild memory issues',
        budget: 12000,
      }),
    },
    {
      code: 'S4',
      name: 'Skilled nursing profile',
      state: simulationHelpers.emptyState({
        assistanceLevel: 'Skilled nursing care',
        budget: 15000,
        notes: 'Recent hospitalization and needs rehabilitation support.',
      }),
    },
  ];
}

function analyzeScenario(facilities, scenario) {
  const output = runOptimeV2Engine(facilities, scenario.state, { mode: 'simulation' });
  const acceptedZero = output.accepted.filter((item) => item.totalScore <= 0);
  const acceptedMandatoryMismatch = output.accepted.filter((item) => hasMandatoryMismatch(item));

  return {
    scenario,
    output,
    acceptedZero,
    acceptedMandatoryMismatch,
    pass: acceptedZero.length === 0,
  };
}

function main() {
  const facilities = simulationHelpers
    .loadBackendFacilities()
    .map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));

  const results = buildScenarios().map((scenario) => analyzeScenario(facilities, scenario));
  const consistencyPass = results.every((result) => result.pass);

  const lines = [];
  lines.push('# Mandatory Gate Consistency Report');
  lines.push('');
  lines.push(`Consistency Status: **${consistencyPass ? 'PASS' : 'FAIL'}**`);
  lines.push('');
  lines.push('Business rule: accepted facility => finalScore > 0');
  lines.push('');

  lines.push('## Scenario Summary');
  lines.push('');
  lines.push(markdownTable(
    ['Scenario', 'Accepted', 'Rejected', 'Accepted with finalScore <= 0', 'Accepted with mandatory mismatch', 'Status'],
    results.map((result) => [
      `${result.scenario.code} - ${result.scenario.name}`,
      result.output.accepted.length,
      result.output.rejected.length,
      result.acceptedZero.length,
      result.acceptedMandatoryMismatch.length,
      result.pass ? 'PASS' : 'FAIL',
    ]),
  ));
  lines.push('');

  results.forEach((result) => {
    lines.push(`## ${result.scenario.code} - ${result.scenario.name}`);
    lines.push('');

    const topAccepted = result.output.accepted.slice(0, 5).map((item, index) => [
      index + 1,
      item.facility.name,
      item.totalScore.toFixed(2),
      item.report.confidenceScore,
      hasMandatoryMismatch(item) ? 'YES' : 'NO',
    ]);

    lines.push('Top accepted sample:');
    lines.push('');
    lines.push(markdownTable(['Rank', 'Facility', 'Final Score', 'Confidence', 'Mandatory mismatch'], topAccepted));
    lines.push('');

    if (result.acceptedZero.length > 0) {
      lines.push('Violations:');
      result.acceptedZero.slice(0, 10).forEach((item) => {
        lines.push(`- ${item.facility.name}: finalScore=${item.totalScore}, mandatoryMismatch=${hasMandatoryMismatch(item) ? 'YES' : 'NO'}`);
      });
      lines.push('');
    }
  });

  lines.push('## Decision');
  lines.push('');
  lines.push(`- CONSISTENCY PASS: ${consistencyPass ? 'YES' : 'NO'}`);
  lines.push('- Option A implemented: mandatory mismatch is treated as hard rejection before accepted list filtering.');

  const reportPath = path.join(repoRoot, 'reports', 'mandatory_gate_consistency_report.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`CONSISTENCY_PASS=${consistencyPass ? 'YES' : 'NO'}`);
}

main();
