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

function collectVerificationChecks(topRecommendations) {
  const unknownNotNo = topRecommendations.every((item) => {
    const unknown = new Set(item.report.audit.clinicalReasoning.unknownCapabilities);
    const rejected = new Set(item.report.audit.clinicalReasoning.rejectedCapabilities);
    for (const capability of unknown) {
      if (rejected.has(capability)) return false;
    }
    return true;
  });

  const unknownAffectsConfidenceOnly = topRecommendations.every((item) => {
    const checklist = item.report.audit.verificationChecklist;
    const unknownCount = checklist.filter((entry) => entry.state === 'UNKNOWN').length;
    const knownCount = checklist.filter((entry) => entry.state === 'YES' || entry.state === 'NO').length;
    const expectedConfidence = (knownCount + unknownCount) > 0
      ? Math.round((knownCount / (knownCount + unknownCount)) * 100)
      : 100;
    return item.report.audit.verificationRequest.confidenceScore === expectedConfidence;
  });

  const verifiedPresentedAsFacts = topRecommendations.every((item) => {
    const verified = new Set(item.report.audit.clinicalReasoning.verifiedCapabilities);
    const unknown = new Set(item.report.audit.clinicalReasoning.unknownCapabilities);
    for (const capability of verified) {
      if (unknown.has(capability)) return false;
    }
    return true;
  });

  const unknownOnlyInVerificationSections = topRecommendations.every((item) => {
    const unknownSet = new Set(item.report.audit.clinicalReasoning.unknownCapabilities);
    const verifiedSet = new Set(item.report.audit.clinicalReasoning.verifiedCapabilities);
    for (const capability of unknownSet) {
      if (verifiedSet.has(capability)) return false;
    }
    const requestItems = item.report.audit.verificationRequest.items.map((entry) => entry.label);
    return requestItems.every((label) => unknownSet.has(label));
  });

  return {
    unknownNotNo,
    unknownAffectsConfidenceOnly,
    verifiedPresentedAsFacts,
    unknownOnlyInVerificationSections,
  };
}

function renderUiNarrativeForTop(top) {
  const clinical = top.report.audit.clinicalReasoning;
  return [
    'Why OPTIME selected this community',
    clinical.whyThisCommunity,
    '',
    'Medical Match',
    clinical.medicalMatch,
    '',
    'Lifestyle Match',
    clinical.lifestyleMatch,
    '',
    'Dietary Match',
    clinical.dietaryMatch,
    '',
    'Social Match',
    clinical.socialMatch,
    '',
    'Future Care Match',
    clinical.futureCareMatch,
    '',
    'Verified capabilities',
    ...(clinical.verifiedCapabilities.length > 0 ? clinical.verifiedCapabilities.map((item) => `✔ ${item}`) : ['No capabilities are fully verified yet.']),
    '',
    'Verification Needed',
    clinical.verificationNeeded,
    ...(clinical.unknownCapabilities.length > 0 ? clinical.unknownCapabilities.map((item) => `❓ ${item}`) : []),
    '',
    'Automatic Facility Verification',
    top.report.audit.verificationRequest.nextStepMessage,
    'To reduce uncertainty before scheduling a visit, OPTIME can contact the community on your behalf to verify open questions. No personal information will be shared.',
  ].join('\n');
}

function buildTopRows(topRecommendations) {
  return topRecommendations.map((item, index) => {
    const clinical = item.report.audit.clinicalReasoning;
    const verified = clinical.verifiedCapabilities.length > 0 ? clinical.verifiedCapabilities.join('; ') : 'None';
    const unknown = clinical.unknownCapabilities.length > 0 ? clinical.unknownCapabilities.join('; ') : 'None';
    const missing = clinical.rejectedCapabilities.length > 0 ? clinical.rejectedCapabilities.join('; ') : 'None';

    return [
      index + 1,
      item.facility.name,
      item.report.finalMatchScore,
      verified,
      unknown,
      missing,
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
    throw new Error('No accepted recommendations produced by engine for this scenario.');
  }

  const best = topRecommendations[0];
  const checks = collectVerificationChecks(topRecommendations);
  const uiNarrative = renderUiNarrativeForTop(best);
  const verificationRequest = best.report.audit.verificationRequest;

  const lines = [];
  lines.push('# Clinical Reasoning E2E Simulation Report');
  lines.push('');
  lines.push('## Scenario');
  lines.push('');
  lines.push('- Resident: Male, age 80 (age group 80-84)');
  lines.push('- Requires 24/7 nursing support');
  lines.push('- Uses walker with significant mobility limitations');
  lines.push('- History of stroke with speech difficulty');
  lines.push('- Lifestyle preferences: movies, music');
  lines.push('- Dietary requirement: gluten-free meals');
  lines.push('- Budget: $12,000/month');
  lines.push('- Move-in timeframe: within 30-60 days');
  lines.push('- Preferred location: Miami-Dade County');
  lines.push('- Future care preference: Full continuum of care on one campus');
  lines.push('');
  lines.push('## Top 5 Communities');
  lines.push('');
  lines.push(markdownTable(
    ['Rank', 'Community', 'OPTIME Match Score', 'Verified requirements matched', 'Unknown requirements', 'Missing requirements', 'Verification readiness score'],
    buildTopRows(topRecommendations),
  ));
  lines.push('');
  lines.push('## Rank #1 Narrative (exact UI text content)');
  lines.push('');
  lines.push('```text');
  lines.push(uiNarrative);
  lines.push('```');
  lines.push('');
  lines.push('## Rank #1 Anonymous Verification Request (exact body sent)');
  lines.push('');
  lines.push(`Subject: ${verificationRequest.subject}`);
  lines.push('');
  lines.push('```text');
  lines.push(verificationRequest.body);
  lines.push('```');
  lines.push('');
  lines.push('## Exact Questions Sent To Facility');
  lines.push('');
  if (best.report.audit.clinicalReasoning.questionsForFacility.length > 0) {
    best.report.audit.clinicalReasoning.questionsForFacility.forEach((question) => {
      lines.push(`- ${question}`);
    });
  } else {
    lines.push('- None (no UNKNOWN requirements).');
  }
  lines.push('');
  lines.push('## Verification Rules Check');
  lines.push('');
  lines.push(`- UNKNOWN items are not treated as NO: **${checks.unknownNotNo ? 'PASS' : 'FAIL'}**`);
  lines.push(`- UNKNOWN items reduce confidence only: **${checks.unknownAffectsConfidenceOnly ? 'PASS' : 'FAIL'}**`);
  lines.push(`- Verified capabilities are presented as facts: **${checks.verifiedPresentedAsFacts ? 'PASS' : 'FAIL'}**`);
  lines.push(`- Unknown capabilities appear only in verification sections: **${checks.unknownOnlyInVerificationSections ? 'PASS' : 'FAIL'}**`);
  lines.push('');
  lines.push('## Return Summary');
  lines.push('');
  lines.push(`- TOP_MATCH_COUNT: ${topRecommendations.length}`);
  lines.push(`- BEST_MATCH: ${best.facility.name}`);
  lines.push(`- MATCH_SCORE: ${best.report.finalMatchScore}`);
  lines.push(`- VERIFICATION_READINESS: ${best.report.audit.verificationReadinessScore}`);
  lines.push(`- UNKNOWN_COUNT: ${best.report.audit.verificationRequest.unknownCount}`);

  const reportPath = path.join(repoRoot, 'reports', 'clinical_reasoning_simulation_report.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`TOP_MATCH_COUNT=${topRecommendations.length}`);
  console.log(`BEST_MATCH=${best.facility.name}`);
  console.log(`MATCH_SCORE=${best.report.finalMatchScore}`);
  console.log(`VERIFICATION_READINESS=${best.report.audit.verificationReadinessScore}`);
  console.log(`UNKNOWN_COUNT=${best.report.audit.verificationRequest.unknownCount}`);
}

main();