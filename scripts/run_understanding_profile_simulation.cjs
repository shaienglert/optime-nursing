const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');

// Reuse this helper to register TypeScript runtime support for importing frontend .ts files.
require('./run_dynamic_persona_simulation_audit.cjs');
const {
  calculateUnderstandingProfile,
  calculateUnderstandingDiagnostics,
} = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'understanding-profile.ts'));

function runCommand(label, command, args, cwd) {
  const isWindowsNpm = process.platform === 'win32' && command === 'npm';
  const result = isWindowsNpm
    ? spawnSync('cmd.exe', ['/d', '/s', '/c', ['npm', ...args].join(' ')], {
      cwd,
      encoding: 'utf8',
      maxBuffer: 20 * 1024 * 1024,
    })
    : spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  const stdout = result.stdout || '';
  const stderr = result.stderr || '';
  return {
    label,
    command: `${command} ${args.join(' ')}`,
    cwd,
    exitCode: result.status,
    output: `${stdout}${stderr}`.trim(),
    passed: result.status === 0,
  };
}

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function makeInput(overrides = {}) {
  return {
    relationship: 'Mom',
    primaryAssistanceLevel: '',
    futureCarePreference: '',
    memoryStatus: '',
    budget: 0,
    happinessPreferences: [],
    preferredEnvironment: [],
    socialInteractionFrequency: '',
    newFriendsImportance: '',
    preferredSocialIntensity: '',
    hobbyParticipation: [],
    religionImportance: '',
    preferredSpokenLanguage: '',
    faithTraditions: [],
    dietaryPreferences: [],
    whatFeelsLikeHome: [],
    familyVisitExpectation: '',
    visitFrequencyExpectation: '',
    normalDriveTime: '',
    parentCurrentHome: '',
    primaryCaregiverHome: '',
    familyCenterOfGravity: '',
    agingInPlaceImportance: '',
    avoidFutureMovesPreference: '',
    continuumOfCarePreference: '',
    secureMemoryNeighborhoodNeed: '',
    familiarLanguageRequirement: '',
    petOwnershipImportance: '',
    ...overrides,
  };
}

function runUnderstandingSimulation() {
  const missingCareManyAnswers = calculateUnderstandingProfile(makeInput({
    budget: 9300,
    happinessPreferences: ['Social activities', 'Movies', 'Outdoor activities', 'Good food'],
    preferredEnvironment: ['Large active community'],
    socialInteractionFrequency: 'Daily',
    newFriendsImportance: 'High',
    preferredSocialIntensity: 'High',
    hobbyParticipation: ['Social activities'],
    religionImportance: 'Important',
    preferredSpokenLanguage: 'English',
    faithTraditions: ['Jewish'],
    dietaryPreferences: ['Kosher'],
    whatFeelsLikeHome: ['Shared traditions'],
    familyVisitExpectation: 'Weekly',
    normalDriveTime: '35',
    futureCarePreference: 'Independent today, support available later',
    avoidFutureMovesPreference: 'Yes',
    continuumOfCarePreference: 'Important',
    familiarLanguageRequirement: 'No',
    petOwnershipImportance: 'Very important',
  }));

  const careCompleteFewerAnswers = calculateUnderstandingProfile(makeInput({
    primaryAssistanceLevel: 'Light assistance',
    memoryStatus: 'Occasionally forgetful',
    budget: 9300,
    socialInteractionFrequency: 'Weekly',
    religionImportance: 'Somewhat important',
    familyVisitExpectation: 'Weekly',
    normalDriveTime: '20',
  }));

  const lowProfile = calculateUnderstandingProfile(makeInput());
  const highProfile = calculateUnderstandingProfile(makeInput({
    relationship: 'Couple',
    primaryAssistanceLevel: 'Light assistance',
    futureCarePreference: 'Full continuum of care on one campus',
    memoryStatus: 'No',
    budget: 11000,
    happinessPreferences: ['Outdoor activities', 'Social activities', 'Good food'],
    preferredEnvironment: ['Large active community', 'Quiet community'],
    socialInteractionFrequency: 'Daily',
    newFriendsImportance: 'Very high',
    preferredSocialIntensity: 'High',
    hobbyParticipation: ['Social activities'],
    religionImportance: 'Important',
    preferredSpokenLanguage: 'English',
    faithTraditions: ['Catholic'],
    dietaryPreferences: ['Mediterranean'],
    whatFeelsLikeHome: ['Family-centered culture'],
    familyVisitExpectation: 'Daily',
    normalDriveTime: '15',
    parentCurrentHome: 'Boca Raton',
    primaryCaregiverHome: 'Delray Beach',
    familyCenterOfGravity: 'Palm Beach County',
    agingInPlaceImportance: 'Very important',
    avoidFutureMovesPreference: 'Yes',
    continuumOfCarePreference: 'Very important',
    secureMemoryNeighborhoodNeed: 'Maybe',
    familiarLanguageRequirement: 'No',
    petOwnershipImportance: 'Important',
  }));

  const checks = [
    {
      name: 'Critical-domain penalty check',
      passed: careCompleteFewerAnswers.understandingScore > missingCareManyAnswers.understandingScore,
      note: `Care-complete score ${careCompleteFewerAnswers.understandingScore}% vs missing-care score ${missingCareManyAnswers.understandingScore}%`,
    },
    {
      name: 'Status text range mapping',
      passed: lowProfile.statusText === 'Getting to know you' && highProfile.statusText === 'Ready for advisor-level recommendations',
      note: `Low=${lowProfile.statusText}; High=${highProfile.statusText}`,
    },
    {
      name: 'Color progression mapping',
      passed: lowProfile.colorBand.label === 'Red' && highProfile.colorBand.label === 'Blue-green',
      note: `Low=${lowProfile.colorBand.label}; High=${highProfile.colorBand.label}`,
    },
    {
      name: 'Journey icon and couple visualization',
      passed: highProfile.personIcon === '👵👴' && highProfile.journeyIcons.filter((icon) => icon.active).length >= 4,
      note: `Person=${highProfile.personIcon}; Active journey icons=${highProfile.journeyIcons.filter((icon) => icon.active).length}`,
    },
    {
      name: 'Recommendation confidence separated from understanding score',
      passed: highProfile.recommendationConfidence !== highProfile.understandingScore,
      note: `Understanding=${highProfile.understandingScore}%; Confidence=${highProfile.recommendationConfidence}%`,
    },
  ];

  const intentionallyIgnoredDistanceInput = makeInput({
    primaryAssistanceLevel: 'Light assistance',
    memoryStatus: 'No',
    budget: 11800,
    happinessPreferences: ['Social activities', 'Outdoor activities', 'Good food'],
    preferredEnvironment: ['Large active community'],
    socialInteractionFrequency: 'Daily',
    newFriendsImportance: 'High',
    preferredSocialIntensity: 'High',
    hobbyParticipation: ['Social activities'],
    religionImportance: 'Not important',
    preferredSpokenLanguage: 'No preference',
    languagePreferenceImportance: 'No preference',
    faithTraditions: ['No religion'],
    dietaryPreferences: ['Mediterranean'],
    whatFeelsLikeHome: ['Shared traditions'],
    familyVisitExpectation: 'Distance not used',
    distancePreference: 'Distance not used',
    futureCarePreference: 'Independent today, support available later',
    avoidFutureMovesPreference: 'Yes',
    continuumOfCarePreference: 'Important',
    familiarLanguageRequirement: 'No preference',
    petOwnershipImportance: 'Not important',
    petPreferenceImportance: 'Not important',
  });

  const explicitDistanceInput = {
    ...intentionallyIgnoredDistanceInput,
    familyVisitExpectation: 'Weekly',
    distancePreference: 'Weekly',
    normalDriveTime: '20',
    parentCurrentHome: 'Boca Raton',
    primaryCaregiverHome: 'Delray Beach',
    familyCenterOfGravity: 'Palm Beach County',
  };

  const intentionallyIgnoredDistance = calculateUnderstandingDiagnostics(intentionallyIgnoredDistanceInput);
  const explicitDistance = calculateUnderstandingDiagnostics(explicitDistanceInput);

  const familyDomainIgnored = intentionallyIgnoredDistance.domainContributions.find((domain) => domain.domainName === 'Family proximity');
  const culturalDomainIgnored = intentionallyIgnoredDistance.domainContributions.find((domain) => domain.domainName === 'Cultural preferences');
  const lifestyleDomainIgnored = intentionallyIgnoredDistance.domainContributions.find((domain) => domain.domainName === 'Lifestyle');

  checks.push({
    name: 'Validation example: all domains answered with distance intentionally ignored',
    passed: intentionallyIgnoredDistance.correctedUnderstandingScore >= 90,
    note: `Corrected understanding score=${intentionallyIgnoredDistance.correctedUnderstandingScore}%`,
  });

  checks.push({
    name: 'Distance not used does not reduce understanding score',
    passed: (familyDomainIgnored?.coverageScore || 0) === 100,
    note: `Family proximity coverage=${familyDomainIgnored?.coverageScore || 0}; intentional_omission=${Boolean(familyDomainIgnored?.intentionalOmission)}`,
  });

  checks.push({
    name: 'Distance not used does not reduce recommendation confidence',
    passed: intentionallyIgnoredDistance.correctedRecommendationConfidence >= explicitDistance.correctedRecommendationConfidence,
    note: `Ignored distance confidence=${intentionallyIgnoredDistance.correctedRecommendationConfidence}% vs explicit distance=${explicitDistance.correctedRecommendationConfidence}%`,
  });

  checks.push({
    name: 'No religion preference gets full understanding credit',
    passed: (culturalDomainIgnored?.coverageScore || 0) === 100,
    note: `Cultural coverage=${culturalDomainIgnored?.coverageScore || 0}; state=${culturalDomainIgnored?.coverageState || 'UNKNOWN'}`,
  });

  checks.push({
    name: 'No language preference gets full understanding credit',
    passed: (culturalDomainIgnored?.coverageScore || 0) === 100,
    note: `Cultural coverage=${culturalDomainIgnored?.coverageScore || 0}; language no-preference counted as NOT_IMPORTANT`,
  });

  checks.push({
    name: 'No pet preference gets full understanding credit',
    passed: (lifestyleDomainIgnored?.coverageScore || 0) === 100,
    note: `Lifestyle coverage=${lifestyleDomainIgnored?.coverageScore || 0}; state=${lifestyleDomainIgnored?.coverageState || 'UNKNOWN'}`,
  });

  return {
    checks,
    pass: checks.every((check) => check.passed),
    rootCause: intentionallyIgnoredDistance,
    comparison: explicitDistance,
  };
}

function parsePassFromOutput(output, regex) {
  const match = output.match(regex);
  return match ? String(match[1]).toUpperCase() === 'PASS' : false;
}

function main() {
  const build = runCommand('Build', 'npm', ['run', 'build'], path.join(repoRoot, 'frontend'));
  const understandingSimulation = runUnderstandingSimulation();

  const dynamicSimulation = runCommand('Dynamic Persona Simulation', 'node', ['scripts/run_dynamic_persona_simulation_audit.cjs'], repoRoot);
  const benchmark = runCommand('Human Advisor Benchmark', 'node', ['scripts/run_human_advisor_benchmark.cjs'], repoRoot);

  const dynamicPass = parsePassFromOutput(dynamicSimulation.output, /Verdict:\s+\*\*(PASS|FAIL)\*\*/i);
  const benchmarkPass = parsePassFromOutput(benchmark.output, /Benchmark status:\s*(PASS|FAIL)/i);
  const regressionPass = dynamicPass && benchmarkPass;

  const overallPass = build.passed && understandingSimulation.pass && regressionPass;

  const lines = [];
  lines.push('# Understanding Profile Validation Report');
  lines.push('');

  const rootCauseLines = [];
  rootCauseLines.push('# Understanding Score Root Cause Report');
  rootCauseLines.push('');
  rootCauseLines.push(`Current score calculation (legacy): **${understandingSimulation.rootCause.legacyUnderstandingScore}%**`);
  rootCauseLines.push(`Expected score calculation (corrected): **${understandingSimulation.rootCause.correctedUnderstandingScore}%**`);
  rootCauseLines.push(`Delta explanation: corrected - legacy = **${understandingSimulation.rootCause.delta}%**`);
  rootCauseLines.push(`Corrected score: **${understandingSimulation.rootCause.correctedUnderstandingScore}%**`);
  rootCauseLines.push(`Corrected recommendation confidence: **${understandingSimulation.rootCause.correctedRecommendationConfidence}%**`);
  rootCauseLines.push('');
  rootCauseLines.push('## Per-domain contribution report');
  rootCauseLines.push('');
  rootCauseLines.push(markdownTable(
    ['Domain', 'Coverage Score', 'Reason', 'Penalty Applied', 'Intentional Omission', 'Coverage State'],
    understandingSimulation.rootCause.domainContributions.map((domain) => [
      domain.domainName,
      domain.coverageScore,
      domain.reason,
      domain.penaltyApplied,
      domain.intentionalOmission,
      domain.coverageState,
    ]),
  ));
  rootCauseLines.push('');
  rootCauseLines.push('## Validation example');
  rootCauseLines.push('');
  rootCauseLines.push('- Inputs: all domains answered, distance intentionally ignored');
  rootCauseLines.push('- Expected: Understanding Score >= 90');
  rootCauseLines.push(`- Actual: **${understandingSimulation.rootCause.correctedUnderstandingScore}%**`);
  rootCauseLines.push('');

  if (understandingSimulation.rootCause.correctedUnderstandingScore < 90) {
    rootCauseLines.push('## Exact penalties responsible for remaining reduction');
    rootCauseLines.push('');
    const penalties = understandingSimulation.rootCause.penalties;
    if (penalties.length > 0) {
      rootCauseLines.push(markdownTable(
        ['Domain', 'Penalty', 'Reason'],
        penalties.map((penalty) => [penalty.domainName, penalty.penaltyApplied, penalty.reason]),
      ));
    } else {
      rootCauseLines.push('- No penalties detected; inspect non-domain adjustments.');
    }
    rootCauseLines.push('');
  }

  const rootCausePath = path.join(repoRoot, 'reports', 'understanding_score_root_cause_report.md');
  fs.writeFileSync(rootCausePath, rootCauseLines.join('\n'));
  lines.push(`Overall Status: **${overallPass ? 'PASS' : 'FAIL'}**`);
  lines.push('');
  lines.push('## Validation Summary');
  lines.push('');
  lines.push(`- Build PASS: **${build.passed ? 'PASS' : 'FAIL'}**`);
  lines.push(`- Simulation PASS: **${understandingSimulation.pass ? 'PASS' : 'FAIL'}**`);
  lines.push(`- No regression in ranking engine: **${regressionPass ? 'PASS' : 'FAIL'}**`);
  lines.push('');
  lines.push('## Understanding Simulation Checks');
  lines.push('');
  lines.push(markdownTable(
    ['Check', 'Verdict', 'Note'],
    understandingSimulation.checks.map((check) => [check.name, check.passed ? 'PASS' : 'FAIL', check.note]),
  ));
  lines.push('');
  lines.push('## Regression Guard Checks');
  lines.push('');
  lines.push(markdownTable(
    ['Command', 'Exit Code', 'Detected Status', 'Verdict'],
    [
      [
        dynamicSimulation.command,
        dynamicSimulation.exitCode,
        dynamicPass ? 'PASS' : 'FAIL',
        dynamicSimulation.passed && dynamicPass ? 'PASS' : 'FAIL',
      ],
      [
        benchmark.command,
        benchmark.exitCode,
        benchmarkPass ? 'PASS' : 'FAIL',
        benchmark.passed && benchmarkPass ? 'PASS' : 'FAIL',
      ],
    ],
  ));
  lines.push('');

  const reportPath = path.join(repoRoot, 'reports', 'understanding_profile_validation_report.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  console.log(`Wrote ${rootCausePath}`);
  console.log(`Wrote ${reportPath}`);
  console.log(`Build PASS=${build.passed ? 'PASS' : 'FAIL'}`);
  console.log(`Simulation PASS=${understandingSimulation.pass ? 'PASS' : 'FAIL'}`);
  console.log(`REGRESSION_PASS=${regressionPass ? 'PASS' : 'FAIL'}`);

  if (!overallPass) {
    process.exitCode = 1;
  }
}

main();
