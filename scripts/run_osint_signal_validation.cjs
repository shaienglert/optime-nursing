const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { CARE_TYPES, loadBackendFacilities, toSearchFacility, emptyState } = simulationHelpers;
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function markdownTable(headers, rows) {
  const escape = (value) => String(value).replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function hasTrustedSources(snapshot) {
  if (!snapshot) return false;
  return snapshot.sources_used.some((source) => ['CMS', 'Medicare Care Compare', 'State inspections', 'AHCA', 'Public court records'].includes(source));
}

function baseState() {
  return emptyState({
    assistanceLevel: 'Fully independent',
    budget: 11000,
    happinessPreferences: ['Movies', 'Social activities'],
    humanIntelligenceV2: {
      ...emptyState().humanIntelligenceV2,
      socialProfile: {
        livingAloneDuration: '6 years',
        socialInteractionFrequency: 'Daily',
        newFriendsImportance: 'High',
        hobbyParticipation: ['Movies', 'Social activities'],
        preferredSocialIntensity: 'High',
      },
      familyProfile: {
        ...emptyState().humanIntelligenceV2.familyProfile,
        visitFrequencyExpectation: 'Weekly',
      },
      distanceProfile: {
        ...emptyState().humanIntelligenceV2.distanceProfile,
        driveTimes: { normal: '20', rushHour: '', emergency: '' },
        familyVisitExpectation: 'Weekly',
      },
    },
  });
}

function cloneWithoutIntelligence(facility) {
  return {
    ...facility,
    intelligenceSnapshot: undefined,
  };
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const enriched = facilities.filter((facility) => facility.intelligenceSnapshot);
  const state = baseState();
  const withOsint = runOptimeV2Engine(facilities, state, { mode: 'simulation' });
  const withoutOsint = runOptimeV2Engine(facilities.map(cloneWithoutIntelligence), state, { mode: 'simulation' });
  const withoutRankMap = new Map(withoutOsint.accepted.map((item, index) => [item.facility.id, { item, rank: index + 1 }]));

  const changedTop10 = withOsint.accepted.slice(0, 10).map((item, index) => {
    const previous = withoutRankMap.get(item.facility.id);
    return {
      name: item.facility.name,
      rankWith: index + 1,
      rankWithout: previous ? previous.rank : 'NR',
      delta: previous ? previous.item.totalScore - item.totalScore : 0,
      trusted: hasTrustedSources(item.facility.intelligenceSnapshot),
      snapshot: item.facility.intelligenceSnapshot,
    };
  });

  const nonTrustedViolations = changedTop10.filter((item) => !item.trusted && Math.abs(item.delta) > 10.01);
  const coverage = Math.round((enriched.length / Math.max(1, facilities.length)) * 100);
  const sourceCoverageRows = facilities.slice(0, 20).map((facility) => [
    facility.name,
    facility.intelligenceSnapshot ? facility.intelligenceSnapshot.sources_used.join('; ') : 'None',
    facility.intelligenceSnapshot ? facility.intelligenceSnapshot.intelligence_confidence : 0,
    facility.intelligenceSnapshot ? facility.intelligenceSnapshot.positive_signals.length : 0,
    facility.intelligenceSnapshot ? facility.intelligenceSnapshot.negative_signals.length : 0,
  ]);

  const status = enriched.length > 0 && nonTrustedViolations.length === 0 ? 'PASS' : 'FAIL';

  const sections = [];
  sections.push('# OSINT Validation Report');
  sections.push('');
  sections.push(`OSINT Validation Status: **${status}**`);
  sections.push(`Intelligence Coverage: **${coverage}%**`);
  sections.push('');
  sections.push('## Impact Check');
  sections.push('');
  sections.push(markdownTable(['Community', 'Rank With OSINT', 'Rank Without OSINT', 'Score Delta', 'Trusted Sources'], changedTop10.map((item) => [item.name, item.rankWith, item.rankWithout, item.delta.toFixed(2), item.trusted ? 'Yes' : 'No'])));
  sections.push('');
  sections.push('## Signal Coverage Sample');
  sections.push('');
  sections.push(markdownTable(['Community', 'Sources Used', 'Confidence', 'Positive Signals', 'Negative Signals'], sourceCoverageRows));
  sections.push('');
  if (nonTrustedViolations.length > 0) {
    sections.push('## Violations');
    sections.push('');
    nonTrustedViolations.forEach((item) => sections.push(`- ${item.name} exceeded the 10-point non-trusted OSINT delta cap (${item.delta.toFixed(2)}).`));
    sections.push('');
  }

  const markdown = sections.join('\n');
  const csvHeaders = ['community', 'rank_with_osint', 'rank_without_osint', 'score_delta', 'trusted_sources', 'intelligence_confidence', 'source_count'];
  const csvRows = changedTop10.map((item) => [
    item.name,
    item.rankWith,
    item.rankWithout,
    item.delta.toFixed(2),
    item.trusted,
    item.snapshot ? item.snapshot.intelligence_confidence : 0,
    item.snapshot ? item.snapshot.sources_used.length : 0,
  ]);
  const csv = [csvHeaders, ...csvRows].map((row) => row.map(csvEscape).join(',')).join('\n');

  const markdownPath = path.join(repoRoot, 'reports', 'osint_validation_report.md');
  const csvPath = path.join(repoRoot, 'reports', 'osint_validation_report.csv');
  fs.writeFileSync(markdownPath, markdown);
  fs.writeFileSync(csvPath, csv);

  console.log(`Wrote ${markdownPath}`);
  console.log(`Wrote ${csvPath}`);
  console.log(markdown);

  if (status !== 'PASS') {
    process.exitCode = 1;
  }
}

main();
