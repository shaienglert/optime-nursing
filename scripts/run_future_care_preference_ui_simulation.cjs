const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

const { loadBackendFacilities, toSearchFacility, emptyState } = simulationHelpers;

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function hasAnyCareType(facility, expected) {
  return facility.careTypes.some((careType) => expected.includes(careType));
}

function isStandaloneClinicalCommunity(facility, careType) {
  const clinicalOnlyTypes = ['Skilled Nursing', 'Rehabilitation', 'Hospice', 'UNKNOWN'];
  return facility.careTypes.includes(careType) && facility.careTypes.every((item) => clinicalOnlyTypes.includes(item));
}

function isContinuumCampus(facility) {
  const hasIndependent = hasAnyCareType(facility, ['Independent Living', 'Active Adult 55+']);
  const hasContinuumLabel = hasAnyCareType(facility, ['CCRC', 'Continuing Care']);
  const hasProgressiveSupport = hasAnyCareType(facility, ['Assisted Living', 'Memory Care', 'Skilled Nursing', 'Rehabilitation']);
  return hasContinuumLabel || (hasIndependent && hasProgressiveSupport && facility.careTypes.length >= 3);
}

function buildScenarioState(preference) {
  const baseline = emptyState();
  return {
    ...baseline,
    ageGroup: '60-64',
    assistanceLevel: 'Fully independent',
    futureCarePreference: preference,
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

function evaluateScenario(name, output) {
  const accepted = output.accepted;
  const top10 = accepted.slice(0, 10);
  const top5 = accepted.slice(0, 5);

  if (name === 'Independent only') {
    const violations = top10.filter((item) => {
      const facility = item.facility;
      const hasIndependent = hasAnyCareType(facility, ['Independent Living', 'Active Adult 55+']);
      const hasExcluded = hasAnyCareType(facility, ['Skilled Nursing', 'Rehabilitation', 'Memory Care']) || /post-acute/i.test(facility.name);
      return !hasIndependent || hasExcluded;
    });

    return {
      pass: violations.length === 0 && accepted.length > 0,
      note: violations.length === 0 ? 'Top 10 stayed independence-only.' : `Found ${violations.length} violating communities in the Top 10.`,
    };
  }

  if (name === 'Future support available') {
    const standaloneClinicalTop10 = top10.filter((item) => isStandaloneClinicalCommunity(item.facility, 'Skilled Nursing') || isStandaloneClinicalCommunity(item.facility, 'Rehabilitation'));
    const independenceReadyTop5 = top5.filter((item) => hasAnyCareType(item.facility, ['Independent Living', 'Active Adult 55+', 'CCRC', 'Continuing Care'])).length;
    return {
      pass: standaloneClinicalTop10.length === 0 && independenceReadyTop5 >= 4,
      note: standaloneClinicalTop10.length === 0
        ? `Top 5 contained ${independenceReadyTop5} independence-first or continuum options.`
        : `Standalone clinical facilities still appeared in the Top 10 (${standaloneClinicalTop10.length}).`,
    };
  }

  const continuumTop5 = top5.filter((item) => isContinuumCampus(item.facility));
  return {
    pass: continuumTop5.length > 0 && isContinuumCampus(accepted[0]?.facility || { careTypes: [] }),
    note: continuumTop5.length > 0
      ? `Top 5 contained ${continuumTop5.length} continuum-oriented communities.`
      : 'No continuum-oriented community reached the Top 5.',
  };
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const scenarios = ['Independent only', 'Future support available', 'Full continuum of care'];

  const rows = [];
  const reportLines = ['# Future Care Preference UI Simulation', ''];

  for (const scenario of scenarios) {
    const state = buildScenarioState(scenario);
    const output = runOptimeV2Engine(facilities, state, { mode: 'production' });
    const verdict = evaluateScenario(scenario, output);
    const top = output.accepted[0];

    rows.push([
      scenario,
      verdict.pass ? 'PASS' : 'FAIL',
      output.accepted.length,
      top?.facility.name || 'None',
      top?.facility.careTypes.join(', ') || 'N/A',
      verdict.note,
    ]);

    reportLines.push(`## ${scenario}`);
    reportLines.push('');
    reportLines.push(`- Verdict: **${verdict.pass ? 'PASS' : 'FAIL'}**`);
    reportLines.push(`- Accepted results: **${output.accepted.length}**`);
    reportLines.push(`- Top result: **${top?.facility.name || 'None'}**`);
    reportLines.push(`- Top result care types: **${top?.facility.careTypes.join(', ') || 'N/A'}**`);
    reportLines.push(`- Validation note: ${verdict.note}`);
    reportLines.push('');
    reportLines.push(markdownTable(
      ['Rank', 'Facility', 'Care Types', 'Score', 'Future Care Contributor'],
      output.accepted.slice(0, 5).map((item, index) => {
        const contributor = item.report.positiveContributors.concat(item.report.negativeContributors).find((entry) => entry.signal.toLowerCase().includes('future care preference'));
        return [
          index + 1,
          item.facility.name,
          item.facility.careTypes.join(', '),
          item.totalScore.toFixed(2),
          contributor ? `${contributor.scoreContribution} | ${contributor.source}` : 'None',
        ];
      }),
    ));
    reportLines.push('');
  }

  const reportPath = path.join(repoRoot, 'reports', 'future_care_preference_ui_simulation.md');
  fs.writeFileSync(reportPath, reportLines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(markdownTable(['Scenario', 'Verdict', 'Accepted', 'Top Result', 'Top Care Types', 'Note'], rows));
  console.log(`UI_PASS=${rows.every((row) => row[1] === 'PASS') ? 'PASS' : 'FAIL'}`);
}

main();
