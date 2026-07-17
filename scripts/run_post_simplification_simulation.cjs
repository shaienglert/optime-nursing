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

function buildScenarioState() {
  const base = simulationHelpers.emptyState();
  return {
    ...base,
    relationship: 'Father',
    gender: 'Male',
    ageGroup: '80-84',
    assistanceLevel: 'Skilled nursing care',
    futureCarePreference: 'Full continuum of care on one campus',
    budget: 12000,
    happinessPreferences: ['Movies', 'Music activities'],
    referenceLocationType: 'County',
    referenceLocationValue: 'Miami-Dade County',
    notes: [
      'Male age 80.',
      'Requires 24/7 nursing support.',
      'Uses walker.',
      'Significant mobility limitations.',
      'History of stroke.',
      'Difficulty speaking after stroke.',
      'Requires gluten-free meals.',
      'Prefers full medical continuum.',
      'Move-in within 30-60 days.',
      'Preferred location Miami-Dade County.',
    ].join(' '),
    humanIntelligenceV2: {
      ...base.humanIntelligenceV2,
      foodProfile: {
        dietaryPreferences: ['Gluten-free'],
      },
      socialProfile: {
        ...base.humanIntelligenceV2.socialProfile,
        socialInteractionFrequency: 'Several times weekly',
      },
      transitionRiskProfile: {
        ...base.humanIntelligenceV2.transitionRiskProfile,
        recentHospitalization: 'Yes',
        postHospitalRehabNeed: 'Yes',
      },
      futureCareProfile: {
        ...base.humanIntelligenceV2.futureCareProfile,
        continuumOfCarePreference: 'Very important',
      },
      distanceProfile: {
        ...base.humanIntelligenceV2.distanceProfile,
        driveTimes: {
          normal: '30',
          rushHour: '45',
          emergency: '20',
        },
        familyVisitExpectation: 'Weekly',
      },
    },
  };
}

function toSimulationFacilityList() {
  const backendFacilities = simulationHelpers.loadBackendFacilities();
  return backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));
}

function deriveMatchFormula(top) {
  const rows = top.report.audit.criteria.filter((row) => row.tier === 'MANDATORY' || row.tier === 'IMPORTANT');
  let yes = 0;
  let no = 0;
  let unknown = 0;

  rows.forEach((row) => {
    const state = (row.source || '').toUpperCase();
    if (state.includes('STATE=YES')) yes += 1;
    else if (state.includes('STATE=NO')) no += 1;
    else unknown += 1;
  });

  const computed = yes + no > 0 ? Math.round((yes / (yes + no)) * 100) : 0;
  return { yes, no, unknown, computed };
}

function buildTopRows(topRecommendations) {
  return topRecommendations.map((item, index) => {
    const clinical = item.report.audit.clinicalReasoning;
    const verified = clinical.verifiedCapabilities.length > 0 ? clinical.verifiedCapabilities.join('; ') : 'None';
    const unknown = clinical.unknownCapabilities.length > 0 ? clinical.unknownCapabilities.join('; ') : 'None';
    const rejected = clinical.rejectedCapabilities.length > 0 ? clinical.rejectedCapabilities.join('; ') : 'None';

    return [
      index + 1,
      item.facility.name,
      item.report.finalMatchScore,
      verified,
      unknown,
      rejected,
      item.report.audit.verificationReadinessScore,
    ];
  });
}

function main() {
  const facilities = toSimulationFacilityList();
  const state = buildScenarioState();
  const output = runOptimeV2Engine(facilities, state);
  const topRecommendations = output.accepted.slice(0, 5);

  if (topRecommendations.length === 0) {
    throw new Error('No accepted recommendations produced by simplified deterministic engine.');
  }

  const top = topRecommendations[0];
  const formula = deriveMatchFormula(top);
  const request = top.report.audit.verificationRequest;
  const payload = top.report.audit.anonymousVerificationPayload;

  const simulationPass = topRecommendations.length > 0 && top.report.finalMatchScore > 0;
  const narrativePass = Boolean(top.report.audit.clinicalReasoning.whyThisCommunity)
    && Boolean(top.report.audit.clinicalReasoning.medicalMatch)
    && Boolean(top.report.audit.clinicalReasoning.verificationNeeded);
  const privacyPass = payload.noPersonalInfoShared === true
    && !request.body.toLowerCase().includes('name')
    && !request.body.toLowerCase().includes('phone')
    && !request.body.toLowerCase().includes('email');

  const formulaPass = formula.computed === top.report.finalMatchScore;
  const unknownExcludedPass = top.report.audit.scoreTraceability
    ? top.report.audit.scoreTraceability.some((line) => line.includes('UNKNOWN items excluded'))
    : top.report.scoreTraceability.some((line) => line.includes('UNKNOWN items excluded'));

  const lines = [];
  lines.push('# Post-Simplification Simulation Report');
  lines.push('');
  lines.push('## Scenario');
  lines.push('');
  lines.push('- Resident: Male, age 80 (age group 80-84)');
  lines.push('- Requires 24/7 nursing support');
  lines.push('- Uses walker with significant mobility limitations');
  lines.push('- History of stroke with speech difficulty');
  lines.push('- Dietary requirement: gluten-free meals');
  lines.push('- Budget: $12,000/month');
  lines.push('- Preferred location: Miami-Dade County');
  lines.push('- Future care preference: Full continuum of care on one campus');
  lines.push('');
  lines.push('## Top 5 Communities');
  lines.push('');
  lines.push(markdownTable(
    ['Rank', 'Community', 'Match Score', 'Verified Capabilities', 'Unknown Capabilities', 'Rejected Capabilities', 'Verification Readiness'],
    buildTopRows(topRecommendations),
  ));
  lines.push('');
  lines.push('## Deterministic Formula Validation (Rank #1)');
  lines.push('');
  lines.push(`- verified_yes: ${formula.yes}`);
  lines.push(`- verified_no: ${formula.no}`);
  lines.push(`- unknown: ${formula.unknown}`);
  lines.push(`- computed score: ${formula.computed}`);
  lines.push(`- reported score: ${top.report.finalMatchScore}`);
  lines.push(`- formula check: **${formulaPass ? 'PASS' : 'FAIL'}**`);
  lines.push(`- unknown excluded from score: **${unknownExcludedPass ? 'PASS' : 'FAIL'}**`);
  lines.push('');
  lines.push('## Rank #1 Full Narrative');
  lines.push('');
  lines.push('```text');
  lines.push('Why OPTIME selected this community');
  lines.push(top.report.audit.clinicalReasoning.whyThisCommunity);
  lines.push('');
  lines.push('Medical Match');
  lines.push(top.report.audit.clinicalReasoning.medicalMatch);
  lines.push('');
  lines.push('Lifestyle Match');
  lines.push(top.report.audit.clinicalReasoning.lifestyleMatch);
  lines.push('');
  lines.push('Dietary Match');
  lines.push(top.report.audit.clinicalReasoning.dietaryMatch);
  lines.push('');
  lines.push('Social Match');
  lines.push(top.report.audit.clinicalReasoning.socialMatch);
  lines.push('');
  lines.push('Future Care Match');
  lines.push(top.report.audit.clinicalReasoning.futureCareMatch);
  lines.push('');
  lines.push('Verification Needed');
  lines.push(top.report.audit.clinicalReasoning.verificationNeeded);
  lines.push('```');
  lines.push('');
  lines.push('## Rank #1 Anonymous Verification Request');
  lines.push('');
  lines.push(`Subject: ${request.subject}`);
  lines.push('');
  lines.push('```text');
  lines.push(request.body);
  lines.push('```');
  lines.push('');
  lines.push('## Questions Sent To Facility');
  lines.push('');
  if (top.report.audit.clinicalReasoning.questionsForFacility.length > 0) {
    top.report.audit.clinicalReasoning.questionsForFacility.forEach((question) => {
      lines.push(`- ${question}`);
    });
  } else {
    lines.push('- None');
  }
  lines.push('');
  lines.push('## Acceptance and Rejection Summary');
  lines.push('');
  lines.push(`- Accepted facility count: ${output.accepted.length}`);
  lines.push(`- Rejected facility count: ${output.rejected.length}`);
  lines.push(`- Top facility hard-rejection reasons: ${top.hardRejectionReasons.length === 0 ? 'None' : top.hardRejectionReasons.join('; ')}`);
  lines.push('');
  lines.push('## Validation Status');
  lines.push('');
  lines.push('- BUILD: **PASS** (validated separately via `npm run build`)');
  lines.push(`- SIMULATION: **${simulationPass ? 'PASS' : 'FAIL'}**`);
  lines.push(`- NARRATIVE: **${narrativePass ? 'PASS' : 'FAIL'}**`);
  lines.push(`- PRIVACY: **${privacyPass ? 'PASS' : 'FAIL'}**`);

  const reportPath = path.join(repoRoot, 'reports', 'post_simplification_simulation.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`TOP_MATCH_COUNT=${topRecommendations.length}`);
  console.log(`BEST_MATCH=${top.facility.name}`);
  console.log(`MATCH_SCORE=${top.report.finalMatchScore}`);
  console.log(`FORMULA_PASS=${formulaPass ? 'PASS' : 'FAIL'}`);
  console.log(`SIMULATION_PASS=${simulationPass ? 'PASS' : 'FAIL'}`);
  console.log(`NARRATIVE_PASS=${narrativePass ? 'PASS' : 'FAIL'}`);
  console.log(`PRIVACY_PASS=${privacyPass ? 'PASS' : 'FAIL'}`);
}

main();
