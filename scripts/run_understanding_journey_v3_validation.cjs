const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');

function runCommand(command, args, cwd) {
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

  return {
    command: `${command} ${args.join(' ')}`,
    exitCode: result.status,
    output: `${result.stdout || ''}${result.stderr || ''}`.trim(),
    passed: result.status === 0,
  };
}

function parsePass(output, regex) {
  const match = output.match(regex);
  return match ? String(match[1]).toUpperCase() === 'PASS' : false;
}

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function evaluateJourneyAndState() {
  const questionnairePath = path.join(repoRoot, 'frontend', 'src', 'app', 'page.tsx');
  const understandingProfilePath = path.join(repoRoot, 'frontend', 'src', 'lib', 'understanding-profile.ts');
  const resultsPath = path.join(repoRoot, 'frontend', 'src', 'app', 'results', 'results-page-client.tsx');
  const questionnaire = fs.readFileSync(questionnairePath, 'utf8');
  const understandingProfile = fs.readFileSync(understandingProfilePath, 'utf8');
  const results = fs.readFileSync(resultsPath, 'utf8');

  const checks = [];

  checks.push({
    name: 'Questionnaire removes recommendation confidence',
    passed: !questionnaire.includes('Recommendation Confidence'),
    note: 'Recommendation confidence text is not present in questionnaire UI.',
  });

  const hiddenInternalTerms = [
    'Care needs',
    'Financial profile',
    'Family proximity',
    'Cultural preferences',
    'Social preferences',
    'Future care planning',
  ];
  const leakedTerms = hiddenInternalTerms.filter((term) => questionnaire.includes(term));
  checks.push({
    name: 'Internal diagnostic domain cards removed',
    passed: leakedTerms.length === 0,
    note: leakedTerms.length === 0 ? 'No internal domain diagnostics rendered.' : `Leaked terms: ${leakedTerms.join(', ')}`,
  });

  const statusSentences = [
    'Getting to know you',
    'Building your lifestyle profile',
    'Understanding what matters most',
    'Ready for advisor-level recommendations',
  ];
  const statusSource = `${questionnaire}\n${understandingProfile}`;
  const missingStatus = statusSentences.filter((sentence) => !statusSource.includes(sentence));
  checks.push({
    name: 'Single status sentence bands present',
    passed: missingStatus.length === 0,
    note: missingStatus.length === 0 ? 'All four status bands are available.' : `Missing: ${missingStatus.join('; ')}`,
  });

  const journeyRenderingPass =
    questionnaire.includes('🏠') &&
    questionnaire.includes('🏘️🌳☕🎭') &&
    questionnaire.includes('sticky top-4') &&
    questionnaire.includes('grayscale') &&
    questionnaire.includes('transition-all duration-700');
  checks.push({
    name: 'Journey rendering and animation rules',
    passed: journeyRenderingPass,
    note: journeyRenderingPass ? 'Journey starts from home, ends at community destination, with sticky and animated progression.' : 'Journey rendering contract not fully detected.',
  });

  const backToSearchPass =
    results.includes('const backToSearch =') &&
    results.includes('router.back()') &&
    !results.match(/const backToSearch[\s\S]*resetState\(/);
  const newSearchPass =
    results.includes('const startNewSearch =') &&
    results.match(/const startNewSearch[\s\S]*resetState\(\)[\s\S]*router\.replace\("\/"\)/);

  checks.push({
    name: 'State persistence (Back to Search)',
    passed: Boolean(backToSearchPass),
    note: backToSearchPass ? 'Back to Search navigates without state reset.' : 'Back to Search state preservation logic missing.',
  });

  checks.push({
    name: 'State reset (New Search)',
    passed: Boolean(newSearchPass),
    note: newSearchPass ? 'New Search resets questionnaire and journey state.' : 'New Search reset logic missing.',
  });

  return checks;
}

function main() {
  const build = runCommand('npm', ['run', 'build'], path.join(repoRoot, 'frontend'));
  const uiChecks = evaluateJourneyAndState();

  const simulation = runCommand('node', ['scripts/run_dynamic_persona_simulation_audit.cjs'], repoRoot);
  const simulationPass = simulation.passed && parsePass(simulation.output, /Verdict:\s+\*\*(PASS|FAIL)\*\*/i);

  const benchmark = runCommand('node', ['scripts/run_human_advisor_benchmark.cjs'], repoRoot);
  const rankingRegressionPass = benchmark.passed && parsePass(benchmark.output, /Benchmark status:\s*(PASS|FAIL)/i);

  const statePersistencePass = uiChecks
    .filter((item) => item.name.includes('State persistence') || item.name.includes('State reset'))
    .every((item) => item.passed);

  const journeyRenderingPass = uiChecks
    .filter((item) => item.name.includes('Questionnaire removes') || item.name.includes('Internal diagnostic') || item.name.includes('Single status') || item.name.includes('Journey rendering'))
    .every((item) => item.passed);

  const overallPass = build.passed && statePersistencePass && journeyRenderingPass && rankingRegressionPass && simulationPass;

  const reportLines = [];
  reportLines.push('# Understanding Journey V3 Validation Report');
  reportLines.push('');
  reportLines.push(`Overall Status: **${overallPass ? 'PASS' : 'FAIL'}**`);
  reportLines.push('');
  reportLines.push('## Validation Summary');
  reportLines.push('');
  reportLines.push(`- Build PASS: **${build.passed ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`- State persistence PASS: **${statePersistencePass ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`- Journey rendering PASS: **${journeyRenderingPass ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`- No ranking regression: **${rankingRegressionPass ? 'PASS' : 'FAIL'}**`);
  reportLines.push('');
  reportLines.push('## UX and State Checks');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Check', 'Verdict', 'Note'],
    uiChecks.map((item) => [item.name, item.passed ? 'PASS' : 'FAIL', item.note]),
  ));
  reportLines.push('');
  reportLines.push('## Runtime Regression Guards');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Command', 'Exit Code', 'Detected Status', 'Verdict'],
    [
      [simulation.command, simulation.exitCode, simulationPass ? 'PASS' : 'FAIL', simulationPass ? 'PASS' : 'FAIL'],
      [benchmark.command, benchmark.exitCode, rankingRegressionPass ? 'PASS' : 'FAIL', rankingRegressionPass ? 'PASS' : 'FAIL'],
    ],
  ));

  const reportPath = path.join(repoRoot, 'reports', 'understanding_journey_v3_validation_report.md');
  fs.writeFileSync(reportPath, reportLines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`Build PASS=${build.passed ? 'PASS' : 'FAIL'}`);
  console.log(`STATE_PERSISTENCE_PASS=${statePersistencePass ? 'PASS' : 'FAIL'}`);
  console.log(`JOURNEY_RENDERING_PASS=${journeyRenderingPass ? 'PASS' : 'FAIL'}`);
  console.log(`RANKING_REGRESSION_PASS=${rankingRegressionPass ? 'PASS' : 'FAIL'}`);

  if (!overallPass) {
    process.exitCode = 1;
  }
}

main();
