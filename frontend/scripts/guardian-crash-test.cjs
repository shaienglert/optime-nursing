#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const frontendRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendRoot, '..');
const simRoot = path.join(frontendRoot, '.guardian-sim');

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeJson(filePath, payload) {
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

function readStatus() {
  const statusPath = path.join(repoRoot, 'reports', 'guardian', 'status.json');
  return JSON.parse(fs.readFileSync(statusPath, 'utf8'));
}

function runGuardianWithFixture(fixturePath) {
  const relativeFixturePath = path.relative(frontendRoot, fixturePath).replace(/\\/g, '/');
  const result = spawnSync('node scripts/guardian.cjs', {
    cwd: frontendRoot,
    shell: true,
    encoding: 'utf8',
    env: {
      ...process.env,
      OPTIME_GUARDIAN_SIM_ONLY: '1',
      OPTIME_GUARDIAN_SIM_FIXTURE: relativeFixturePath,
    },
  });

  const status = readStatus();
  return {
    exitCode: result.status ?? 1,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
    verdict: status.verdict,
  };
}

function runDeploymentGateSimulation(expectStop) {
  const deploymentFixturePath = path.join(simRoot, 'deployment-gate.json');
  const guardianRun = runGuardianWithFixture(deploymentFixturePath);
  const downstreamExecuted = guardianRun.exitCode === 0;
  const downstreamStopped = guardianRun.exitCode !== 0;

  const outputLines = [
    `GUARDIAN_EXIT=${guardianRun.exitCode}`,
    `GUARDIAN_VERDICT=${guardianRun.verdict}`,
  ];

  if (downstreamExecuted) {
    outputLines.push('DOWNSTREAM_EXECUTED');
  } else {
    outputLines.push('DOWNSTREAM_NOT_EXECUTED');
  }

  const output = outputLines.join('\n');

  return {
    exitCode: guardianRun.exitCode,
    output,
    downstreamExecuted,
    downstreamStopped,
    passed: expectStop ? downstreamStopped && !downstreamExecuted : downstreamExecuted,
  };
}

function asRow(values, widths) {
  return values
    .map((value, index) => String(value).padEnd(widths[index], ' '))
    .join(' | ');
}

function printTable(rows) {
  const headers = ['TEST', 'ATTACK', 'EXPECTED', 'ACTUAL', 'EXIT CODE', 'PROCESS STOPPED', 'RESULT'];
  const widths = headers.map((header, index) => {
    const contentWidths = rows.map((row) => String(row[index]).length);
    return Math.max(header.length, ...contentWidths);
  });

  console.log('');
  console.log(asRow(headers, widths));
  console.log(widths.map((width) => '-'.repeat(width)).join('-|-'));
  for (const row of rows) {
    console.log(asRow(row, widths));
  }
  console.log('');
}

function main() {
  ensureDir(simRoot);

  const attacks = [
    {
      id: 'ATTACK-1',
      title: 'DATA TRUTH',
      fixture: {
        scenarioId: 'ATTACK-1',
        mode: 'attack',
        dataTruth: { jobSourceType: 'SYNTHETIC', attemptedReportedAs: 'REAL' },
      },
    },
    {
      id: 'ATTACK-2',
      title: 'MUST VIOLATION',
      fixture: {
        scenarioId: 'ATTACK-2',
        mode: 'attack',
        mustRule: {
          candidateMinTeamSize: 10,
          requirementLevel: 'MUST',
          jobTeamSize: 2,
          attemptedOutcome: 'ALLOW',
        },
      },
    },
    {
      id: 'ATTACK-3',
      title: 'UNKNOWN CORRUPTION',
      fixture: {
        scenarioId: 'ATTACK-3',
        mode: 'attack',
        unknownRule: {
          candidateMinTeamSize: 10,
          jobTeamSize: null,
          attemptedOutcome: 'MATCH',
          evidenceIds: [],
        },
      },
    },
    {
      id: 'ATTACK-4',
      title: 'UNSUPPORTED LEARNING',
      fixture: {
        scenarioId: 'ATTACK-4',
        mode: 'attack',
        learningRule: {
          rejectedTravelJobs: 4,
          attemptedMutation: 'NO_TRAVEL',
          evidenceIds: [],
          userApproval: false,
        },
      },
    },
    {
      id: 'ATTACK-5',
      title: 'PRIVACY',
      fixture: {
        scenarioId: 'ATTACK-5',
        mode: 'attack',
        privacyRule: {
          isPrivate: true,
          attemptPublicSearchable: true,
          explicitConsent: false,
        },
      },
    },
    {
      id: 'ATTACK-6',
      title: 'SEARCH APPROVAL',
      fixture: {
        scenarioId: 'ATTACK-6',
        mode: 'attack',
        searchRule: {
          hasCareerDNA: true,
          hasSearchIntent: true,
          searchIntentApproval: false,
          attemptExecuteSearch: true,
        },
      },
    },
  ];

  const legal = [
    {
      id: 'LEGAL-1',
      title: 'DATA TRUTH COMPLIANT',
      fixture: {
        scenarioId: 'LEGAL-1',
        mode: 'legal',
        dataTruth: { jobSourceType: 'SYNTHETIC', attemptedReportedAs: 'SYNTHETIC' },
      },
    },
    {
      id: 'LEGAL-2',
      title: 'MUST EXCLUSION COMPLIANT',
      fixture: {
        scenarioId: 'LEGAL-2',
        mode: 'legal',
        mustRule: {
          candidateMinTeamSize: 10,
          requirementLevel: 'MUST',
          jobTeamSize: 2,
          attemptedOutcome: 'EXCLUDE',
        },
      },
    },
    {
      id: 'LEGAL-3',
      title: 'UNKNOWN RETAINED COMPLIANT',
      fixture: {
        scenarioId: 'LEGAL-3',
        mode: 'legal',
        unknownRule: {
          candidateMinTeamSize: 10,
          jobTeamSize: null,
          attemptedOutcome: 'UNKNOWN',
          evidenceIds: [],
        },
      },
    },
    {
      id: 'LEGAL-4',
      title: 'LEARNING EVIDENCED COMPLIANT',
      fixture: {
        scenarioId: 'LEGAL-4',
        mode: 'legal',
        learningRule: {
          rejectedTravelJobs: 4,
          attemptedMutation: 'NO_TRAVEL',
          evidenceIds: ['ev-1', 'ev-2'],
          userApproval: true,
        },
      },
    },
    {
      id: 'LEGAL-5',
      title: 'PRIVACY CONSENT COMPLIANT',
      fixture: {
        scenarioId: 'LEGAL-5',
        mode: 'legal',
        privacyRule: {
          isPrivate: true,
          attemptPublicSearchable: true,
          explicitConsent: true,
        },
      },
    },
    {
      id: 'LEGAL-6',
      title: 'SEARCH APPROVAL COMPLIANT',
      fixture: {
        scenarioId: 'LEGAL-6',
        mode: 'legal',
        searchRule: {
          hasCareerDNA: true,
          hasSearchIntent: true,
          searchIntentApproval: true,
          attemptExecuteSearch: true,
        },
      },
    },
  ];

  const tableRows = [];
  const detailedOutputs = [];

  let attacksBlocked = 0;
  let falsePasses = 0;

  for (const test of attacks) {
    const fixturePath = path.join(simRoot, `${test.id}.json`);
    writeJson(fixturePath, test.fixture);
    const run = runGuardianWithFixture(fixturePath);
    const stopped = run.exitCode !== 0;
    const ok = stopped && run.verdict === 'BLOCK';

    if (ok) {
      attacksBlocked += 1;
    } else {
      falsePasses += 1;
    }

    tableRows.push([
      test.id,
      test.title,
      'GUARDIAN BLOCK',
      `GUARDIAN ${run.verdict}`,
      run.exitCode,
      stopped ? 'YES' : 'NO',
      ok ? 'PASS' : 'FAIL',
    ]);

    detailedOutputs.push({ id: test.id, output: run.stdout.trim(), stderr: run.stderr.trim(), exitCode: run.exitCode });
  }

  let legalPassed = 0;
  let falseBlocks = 0;

  for (const test of legal) {
    const fixturePath = path.join(simRoot, `${test.id}.json`);
    writeJson(fixturePath, test.fixture);
    const run = runGuardianWithFixture(fixturePath);
    const stopped = run.exitCode !== 0;
    const ok = !stopped && run.verdict === 'PASS';

    if (ok) {
      legalPassed += 1;
    } else {
      falseBlocks += 1;
    }

    tableRows.push([
      test.id,
      test.title,
      'GUARDIAN PASS',
      `GUARDIAN ${run.verdict}`,
      run.exitCode,
      stopped ? 'YES' : 'NO',
      ok ? 'PASS' : 'FAIL',
    ]);

    detailedOutputs.push({ id: test.id, output: run.stdout.trim(), stderr: run.stderr.trim(), exitCode: run.exitCode });
  }

  const deployAttackFixture = {
    scenarioId: 'DEPLOYMENT-KILL-BLOCK',
    mode: 'attack',
    searchRule: {
      hasCareerDNA: true,
      hasSearchIntent: true,
      searchIntentApproval: false,
      attemptExecuteSearch: true,
    },
  };
  writeJson(path.join(simRoot, 'deployment-gate.json'), deployAttackFixture);
  const deploymentBlocked = runDeploymentGateSimulation(true);

  const deployLegalFixture = {
    scenarioId: 'DEPLOYMENT-KILL-PASS',
    mode: 'legal',
    searchRule: {
      hasCareerDNA: true,
      hasSearchIntent: true,
      searchIntentApproval: true,
      attemptExecuteSearch: true,
    },
  };
  writeJson(path.join(simRoot, 'deployment-gate.json'), deployLegalFixture);
  const deploymentAllowed = runDeploymentGateSimulation(false);

  printTable(tableRows);

  console.log('ACTUAL COMMAND OUTPUTS');
  for (const entry of detailedOutputs) {
    console.log(`\\n[${entry.id}] exit=${entry.exitCode}`);
    if (entry.output) {
      console.log(entry.output);
    }
    if (entry.stderr) {
      console.log(entry.stderr);
    }
  }

  console.log('\\nDEPLOYMENT KILL TEST OUTPUTS');
  console.log(`[BLOCK FIXTURE] exit=${deploymentBlocked.exitCode}`);
  console.log(deploymentBlocked.output.trim());
  console.log(`[LEGAL FIXTURE] exit=${deploymentAllowed.exitCode}`);
  console.log(deploymentAllowed.output.trim());

  const finalVerdict = falsePasses > 0 ? 'GUARDIAN FAILED' : 'GUARDIAN PASSED';
  const productionReady = falsePasses === 0 && falseBlocks === 0 && deploymentBlocked.passed && deploymentAllowed.passed;

  console.log('\\nGUARDIAN CRASH TEST');
  console.log(`- Attacks tested: ${attacks.length}`);
  console.log(`- Attacks blocked: ${attacksBlocked}`);
  console.log(`- False passes: ${falsePasses}`);
  console.log(`- Legal scenarios tested: ${legal.length}`);
  console.log(`- Legal scenarios passed: ${legalPassed}`);
  console.log(`- False blocks: ${falseBlocks}`);
  console.log(`- Deployment blocked by Guardian: ${deploymentBlocked.passed ? 'YES' : 'NO'}`);
  console.log(`- Deployment allowed after correction: ${deploymentAllowed.passed ? 'YES' : 'NO'}`);
  console.log(`- Final Guardian verdict: ${finalVerdict}`);
  console.log(`- Guardian production-ready: ${productionReady ? 'YES' : 'NO'}`);

  const crashReport = {
    generatedAt: new Date().toISOString(),
    attacksTested: attacks.length,
    attacksBlocked,
    falsePasses,
    legalScenariosTested: legal.length,
    legalScenariosPassed: legalPassed,
    falseBlocks,
    deploymentBlockedByGuardian: deploymentBlocked.passed,
    deploymentAllowedAfterCorrection: deploymentAllowed.passed,
    finalGuardianVerdict: finalVerdict,
    guardianProductionReady: productionReady,
    table: tableRows,
  };

  const reportPath = path.join(repoRoot, 'reports', 'guardian', 'crash-test-report.json');
  ensureDir(path.dirname(reportPath));
  writeJson(reportPath, crashReport);

  process.exit(productionReady ? 0 : 1);
}

main();
