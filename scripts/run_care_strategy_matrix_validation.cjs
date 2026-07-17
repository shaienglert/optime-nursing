const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine, resolveAllowedCareTypes } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function sameSet(left, right) {
  if (left.length !== right.length) return false;
  const leftSorted = [...left].sort();
  const rightSorted = [...right].sort();
  return leftSorted.every((value, idx) => value === rightSorted[idx]);
}

function supportsAllowedCareType(facility, allowedCareTypes) {
  return facility.careTypes.some((careType) => {
    if (allowedCareTypes.includes(careType)) return true;
    return careType === 'Continuing Care' && allowedCareTypes.includes('CCRC');
  });
}

function scenarioState(scenarioName) {
  const base = simulationHelpers.emptyState();

  if (scenarioName === 'Fully Independent + Independent only') {
    return {
      ...base,
      assistanceLevel: 'Fully independent',
      futureCarePreference: 'Independent communities only',
      memoryStatus: 'No',
      budget: 11000,
    };
  }

  if (scenarioName === 'Fully Independent + Support available later') {
    return {
      ...base,
      assistanceLevel: 'Fully independent',
      futureCarePreference: 'Independent today, support available later',
      memoryStatus: 'No',
      budget: 11000,
    };
  }

  if (scenarioName === 'Fully Independent + Full continuum') {
    return {
      ...base,
      assistanceLevel: 'Fully independent',
      futureCarePreference: 'Full continuum of care on one campus',
      memoryStatus: 'No',
      budget: 11000,
    };
  }

  if (scenarioName === 'Light Assistance') {
    return {
      ...base,
      assistanceLevel: 'Some daily support',
      futureCarePreference: 'No preference',
      memoryStatus: 'No',
      budget: 11000,
    };
  }

  if (scenarioName === 'Memory Support') {
    return {
      ...base,
      assistanceLevel: 'Some daily support',
      futureCarePreference: 'No preference',
      memoryStatus: 'Significant memory issues',
      budget: 12000,
    };
  }

  return {
    ...base,
    assistanceLevel: 'Skilled nursing care',
    futureCarePreference: 'No preference',
    memoryStatus: 'No',
    notes: 'Post-hospital rehabilitation and complex medical support required.',
    budget: 15000,
  };
}

function main() {
  const expectedRows = [
    {
      scenario: 'Fully Independent + Independent only',
      currentCareNeed: 'Fully Independent',
      futureCarePreference: 'Independent communities only',
      expected: ['Independent Living', 'Active Adult 55+'],
    },
    {
      scenario: 'Fully Independent + Support available later',
      currentCareNeed: 'Fully Independent',
      futureCarePreference: 'Independent today, support available later',
      expected: ['Independent Living', 'Active Adult 55+', 'Assisted Living', 'CCRC'],
    },
    {
      scenario: 'Fully Independent + Full continuum',
      currentCareNeed: 'Fully Independent',
      futureCarePreference: 'Full continuum of care on one campus',
      expected: ['Independent Living', 'Assisted Living', 'Memory Care', 'CCRC'],
    },
    {
      scenario: 'Light Assistance',
      currentCareNeed: 'Light Assistance',
      futureCarePreference: 'No preference',
      expected: ['Assisted Living', 'CCRC'],
    },
    {
      scenario: 'Memory Support',
      currentCareNeed: 'Memory Support',
      futureCarePreference: 'No preference',
      expected: ['Memory Care', 'CCRC'],
    },
    {
      scenario: 'Complex Medical Needs',
      currentCareNeed: 'Complex Medical Needs',
      futureCarePreference: 'No preference',
      expected: ['Skilled Nursing', 'Rehabilitation'],
    },
  ];

  const facilities = simulationHelpers
    .loadBackendFacilities()
    .map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));

  const rows = [];
  let matrixPass = true;

  expectedRows.forEach((item) => {
    const actual = resolveAllowedCareTypes(item.currentCareNeed, item.futureCarePreference);
    const mappingPass = sameSet(actual, item.expected);

    const output = runOptimeV2Engine(facilities, scenarioState(item.scenario), { mode: 'simulation' });
    const acceptedViolations = output.accepted.filter((recommendation) => !supportsAllowedCareType(recommendation.facility, actual));
    const acceptedRulePass = acceptedViolations.length === 0;

    const rowPass = mappingPass && acceptedRulePass;
    matrixPass = matrixPass && rowPass;

    rows.push([
      item.scenario,
      item.expected.join(', '),
      actual.join(', '),
      mappingPass ? 'PASS' : 'FAIL',
      output.accepted.length,
      acceptedViolations.length,
      acceptedRulePass ? 'PASS' : 'FAIL',
      rowPass ? 'PASS' : 'FAIL',
    ]);
  });

  const lines = [];
  lines.push('# Care Strategy Matrix Validation');
  lines.push('');
  lines.push(`CARE_STRATEGY_MATRIX: **${matrixPass ? 'PASS' : 'FAIL'}**`);
  lines.push('');
  lines.push(markdownTable(
    [
      'Scenario',
      'Expected allowedCareTypes',
      'Actual allowedCareTypes',
      'Mapping',
      'Accepted count',
      'Accepted rule violations',
      'Accepted rule',
      'Status',
    ],
    rows,
  ));

  const reportPath = path.join(repoRoot, 'reports', 'care_strategy_matrix_validation.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`CARE_STRATEGY_MATRIX=${matrixPass ? 'PASS' : 'FAIL'}`);
}

main();
