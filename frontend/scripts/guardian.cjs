#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const STATUS = {
  PASS: 'PASS',
  WARN: 'WARN',
  BLOCK: 'BLOCK',
};

const SEVERITY = {
  LOW: 'LOW',
  MEDIUM: 'MEDIUM',
  HIGH: 'HIGH',
  CRITICAL: 'CRITICAL',
};

const frontendRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendRoot, '..');
const reportsRoot = path.join(repoRoot, 'reports', 'guardian');
const incidentsRoot = path.join(reportsRoot, 'incidents');
const simulationFixturePath = process.env.OPTIME_GUARDIAN_SIM_FIXTURE
  ? path.resolve(frontendRoot, process.env.OPTIME_GUARDIAN_SIM_FIXTURE)
  : null;
const simulationOnly = process.env.OPTIME_GUARDIAN_SIM_ONLY === '1';

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function readTextSafe(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch {
    return null;
  }
}

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function exists(filePath) {
  return fs.existsSync(filePath);
}

function runCommand(command) {
  const result = spawnSync(command, {
    cwd: frontendRoot,
    shell: true,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  return {
    ok: result.status === 0,
    code: result.status,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
  };
}

function collectFiles(rootDir) {
  const entries = fs.readdirSync(rootDir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const abs = path.join(rootDir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === '.next') {
        continue;
      }
      files.push(...collectFiles(abs));
    } else {
      files.push(abs);
    }
  }

  return files;
}

function moduleResult(moduleId, title) {
  return {
    moduleId,
    title,
    findings: [],
    status: STATUS.PASS,
  };
}

function addFinding(mod, finding) {
  mod.findings.push(finding);
  if (finding.status === STATUS.BLOCK) {
    mod.status = STATUS.BLOCK;
    return;
  }
  if (finding.status === STATUS.WARN && mod.status !== STATUS.BLOCK) {
    mod.status = STATUS.WARN;
  }
}

function checkConstitutionAudit() {
  const mod = moduleResult('constitution-audit', 'Constitution Audit');

  const checks = [
    {
      filePath: path.join(repoRoot, 'AGENTS.md'),
      mustContain: ['Mandatory Pre-Change Principle Impact Check', 'Classification Gate'],
      ruleId: 'GUARD-CON-001',
    },
    {
      filePath: path.join(repoRoot, 'docs', 'OPTIME_PRINCIPLES.md'),
      mustContain: ['No evidence, no score', 'Missing information is not negative evidence'],
      ruleId: 'GUARD-CON-002',
    },
    {
      filePath: path.join(repoRoot, 'docs', 'OPTIME_PRINCIPLES_REGISTRY.md'),
      mustContain: ['Principle Impact Check', 'OWNER APPROVAL REQUIRED'],
      ruleId: 'GUARD-CON-003',
    },
  ];

  for (const check of checks) {
    if (!exists(check.filePath)) {
      addFinding(mod, {
        ruleId: check.ruleId,
        severity: SEVERITY.CRITICAL,
        status: STATUS.BLOCK,
        message: 'Required governance source is missing.',
        evidence: [path.relative(repoRoot, check.filePath)],
        filePath: path.relative(repoRoot, check.filePath),
        requiredAction: 'Restore the missing governance document before merging.',
      });
      continue;
    }

    const text = readTextSafe(check.filePath) || '';
    const missing = check.mustContain.filter((token) => !text.includes(token));
    if (missing.length > 0) {
      addFinding(mod, {
        ruleId: check.ruleId,
        severity: SEVERITY.HIGH,
        status: STATUS.BLOCK,
        message: 'Governance source exists but is missing required constitutional language.',
        evidence: missing,
        filePath: path.relative(repoRoot, check.filePath),
        requiredAction: 'Restore mandatory principle text exactly as approved.',
      });
    } else {
      addFinding(mod, {
        ruleId: check.ruleId,
        severity: SEVERITY.LOW,
        status: STATUS.PASS,
        message: 'Governance source is present and includes required constitutional clauses.',
        evidence: ['OK'],
        filePath: path.relative(repoRoot, check.filePath),
        requiredAction: 'None.',
      });
    }
  }

  return mod;
}

function checkDecisionSymmetryAudit() {
  const mod = moduleResult('decision-symmetry-audit', 'Decision Symmetry Audit');
  const contractPath = path.join(frontendRoot, 'src', 'os', 'contracts.ts');

  if (!exists(contractPath)) {
    addFinding(mod, {
      ruleId: 'GUARD-SYM-001',
      severity: SEVERITY.CRITICAL,
      status: STATUS.BLOCK,
      message: 'OS contract boundary file is missing.',
      evidence: ['frontend/src/os/contracts.ts'],
      filePath: 'frontend/src/os/contracts.ts',
      requiredAction: 'Restore OS contracts boundary file.',
    });
  } else {
    const text = readTextSafe(contractPath) || '';
    if (/^import\s/m.test(text)) {
      addFinding(mod, {
        ruleId: 'GUARD-SYM-001',
        severity: SEVERITY.HIGH,
        status: STATUS.BLOCK,
        message: 'OS contract boundary has imports, violating import-free boundary rule.',
        evidence: ['Found import statement in OS contracts.'],
        filePath: 'frontend/src/os/contracts.ts',
        requiredAction: 'Keep OS boundary contract import-free.',
      });
    } else {
      addFinding(mod, {
        ruleId: 'GUARD-SYM-001',
        severity: SEVERITY.LOW,
        status: STATUS.PASS,
        message: 'OS contract boundary remains import-free.',
        evidence: ['No imports found.'],
        filePath: 'frontend/src/os/contracts.ts',
        requiredAction: 'None.',
      });
    }
  }

  const boundaryTest = runCommand('npm run test:os-boundary');
  if (!boundaryTest.ok) {
    addFinding(mod, {
      ruleId: 'GUARD-SYM-002',
      severity: SEVERITY.CRITICAL,
      status: STATUS.BLOCK,
      message: 'Decision symmetry boundary tests failed.',
      evidence: [boundaryTest.stderr || boundaryTest.stdout || `Exit code ${boundaryTest.code}`],
      filePath: 'frontend/tests/os-adapter.test.ts',
      requiredAction: 'Fix boundary tests before merge or deploy.',
    });
  } else {
    addFinding(mod, {
      ruleId: 'GUARD-SYM-002',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'Decision symmetry boundary tests passed.',
      evidence: ['npm run test:os-boundary passed'],
      filePath: 'frontend/tests/os-adapter.test.ts',
      requiredAction: 'None.',
    });
  }

  return mod;
}

function checkEvidenceAndProvenanceAudit() {
  const mod = moduleResult('evidence-provenance-audit', 'Evidence & Provenance Audit');

  const requiredFiles = [
    'database/recommendation_traceability_matrix.json',
    'database/facility_evidence_matrix_snapshot.json',
    'database/facility_evidence_matrix_schema.json',
  ];

  for (const rel of requiredFiles) {
    const abs = path.join(repoRoot, rel);
    if (!exists(abs)) {
      addFinding(mod, {
        ruleId: 'GUARD-EVP-001',
        severity: SEVERITY.CRITICAL,
        status: STATUS.BLOCK,
        message: 'Required evidence/provenance artifact is missing.',
        evidence: [rel],
        filePath: rel,
        requiredAction: 'Restore required evidence matrix and traceability artifacts.',
      });
      continue;
    }

    const parsed = readJsonSafe(abs);
    if (parsed === null) {
      addFinding(mod, {
        ruleId: 'GUARD-EVP-002',
        severity: SEVERITY.HIGH,
        status: STATUS.BLOCK,
        message: 'Evidence/provenance artifact is not valid JSON.',
        evidence: [rel],
        filePath: rel,
        requiredAction: 'Fix JSON integrity of provenance artifact.',
      });
      continue;
    }

    addFinding(mod, {
      ruleId: 'GUARD-EVP-003',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'Evidence/provenance artifact exists and is valid JSON.',
      evidence: [rel],
      filePath: rel,
      requiredAction: 'None.',
    });
  }

  return mod;
}

function checkLearningSafetyAudit() {
  const mod = moduleResult('learning-safety-audit', 'Learning Safety Audit');
  const registryPath = path.join(repoRoot, 'docs', 'OPTIME_PRINCIPLES_REGISTRY.md');
  const enginePath = path.join(frontendRoot, 'src', 'lib', 'optime-v2-engine.ts');

  const registryText = readTextSafe(registryPath) || '';
  const requiredRegistryTokens = [
    'No Evidence, No Score',
    'Unknown Is Not Negative Evidence',
    'Owner approval is mandatory for principle-level semantic changes',
  ];

  const missingRegistry = requiredRegistryTokens.filter((token) => !registryText.includes(token));
  if (missingRegistry.length > 0) {
    addFinding(mod, {
      ruleId: 'GUARD-LRN-001',
      severity: SEVERITY.HIGH,
      status: STATUS.BLOCK,
      message: 'Learning governance registry is missing required safety clauses.',
      evidence: missingRegistry,
      filePath: 'docs/OPTIME_PRINCIPLES_REGISTRY.md',
      requiredAction: 'Restore missing governance clauses before changing learning behavior.',
    });
  } else {
    addFinding(mod, {
      ruleId: 'GUARD-LRN-001',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'Learning governance registry includes required safety clauses.',
      evidence: ['Registry safety clauses present.'],
      filePath: 'docs/OPTIME_PRINCIPLES_REGISTRY.md',
      requiredAction: 'None.',
    });
  }

  if (!exists(enginePath)) {
    addFinding(mod, {
      ruleId: 'GUARD-LRN-002',
      severity: SEVERITY.MEDIUM,
      status: STATUS.WARN,
      message: 'Ranking engine file not found for local learning safety lexical checks.',
      evidence: ['frontend/src/lib/optime-v2-engine.ts missing'],
      filePath: 'frontend/src/lib/optime-v2-engine.ts',
      requiredAction: 'Review learning safety rules manually.',
    });
  } else {
    const engineText = readTextSafe(enginePath) || '';
    const hasUnknown = engineText.includes('UNKNOWN');
    const hasInsufficientEvidence = /insufficient evidence/i.test(engineText);

    if (!hasUnknown || !hasInsufficientEvidence) {
      addFinding(mod, {
        ruleId: 'GUARD-LRN-003',
        severity: SEVERITY.LOW,
        status: STATUS.PASS,
        message: 'Engine lexical signals for UNKNOWN and insufficient-evidence handling are incomplete.',
        evidence: [
          `UNKNOWN token present: ${hasUnknown}`,
          `insufficient evidence messaging present: ${hasInsufficientEvidence}`,
        ],
        filePath: 'frontend/src/lib/optime-v2-engine.ts',
        requiredAction: 'Optional: align UX wording to explicitly include "insufficient evidence" phrasing.',
      });
    } else {
      addFinding(mod, {
        ruleId: 'GUARD-LRN-003',
        severity: SEVERITY.LOW,
        status: STATUS.PASS,
        message: 'Engine includes lexical markers for UNKNOWN and insufficient evidence handling.',
        evidence: ['UNKNOWN and insufficient evidence markers found.'],
        filePath: 'frontend/src/lib/optime-v2-engine.ts',
        requiredAction: 'None.',
      });
    }
  }

  return mod;
}

function checkSimulationPolicyAudit() {
  const mod = moduleResult('simulation-policy-audit', 'Simulation Policy Audit');

  if (!simulationFixturePath) {
    addFinding(mod, {
      ruleId: 'GUARD-SIM-000',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'No simulation fixture provided; attack simulation audit skipped.',
      evidence: ['Set OPTIME_GUARDIAN_SIM_FIXTURE to execute crash simulation checks.'],
      filePath: 'frontend/scripts/guardian.cjs',
      requiredAction: 'None.',
    });
    return mod;
  }

  const fixture = readJsonSafe(simulationFixturePath);
  if (!fixture) {
    addFinding(mod, {
      ruleId: 'GUARD-SIM-001',
      severity: SEVERITY.HIGH,
      status: STATUS.BLOCK,
      message: 'Simulation fixture is unreadable or invalid JSON.',
      evidence: [path.relative(repoRoot, simulationFixturePath)],
      filePath: path.relative(repoRoot, simulationFixturePath),
      requiredAction: 'Fix simulation fixture JSON before running enforcement simulation.',
    });
    return mod;
  }

  const scenarioId = String(fixture.scenarioId || 'UNKNOWN_SCENARIO');
  const mode = String(fixture.mode || 'attack').toLowerCase();

  function addPolicyFinding(ruleId, violated, message, filePath, evidence, requiredAction) {
    addFinding(mod, {
      ruleId,
      severity: violated ? SEVERITY.CRITICAL : SEVERITY.LOW,
      status: violated ? STATUS.BLOCK : STATUS.PASS,
      message,
      evidence,
      filePath,
      requiredAction,
    });
  }

  const dataTruth = fixture.dataTruth || {};
  const dataTruthViolation =
    String(dataTruth.jobSourceType || '').toUpperCase() === 'SYNTHETIC' &&
    String(dataTruth.attemptedReportedAs || '').toUpperCase() === 'REAL';
  addPolicyFinding(
    'GUARD-SIM-101',
    dataTruthViolation,
    dataTruthViolation
      ? `[${scenarioId}] Synthetic job attempted to be reported as REAL.`
      : `[${scenarioId}] Data truth classification remains compliant.`,
    path.relative(repoRoot, simulationFixturePath),
    [
      `jobSourceType=${dataTruth.jobSourceType ?? 'UNKNOWN'}`,
      `attemptedReportedAs=${dataTruth.attemptedReportedAs ?? 'UNKNOWN'}`,
      `mode=${mode}`,
    ],
    dataTruthViolation ? 'Keep synthetic entities classified as SYNTHETIC.' : 'None.',
  );

  const mustRule = fixture.mustRule || {};
  const mustViolation =
    String(mustRule.requirementLevel || '').toUpperCase() === 'MUST' &&
    Number.isFinite(mustRule.candidateMinTeamSize) &&
    Number.isFinite(mustRule.jobTeamSize) &&
    Number(mustRule.jobTeamSize) < Number(mustRule.candidateMinTeamSize) &&
    String(mustRule.attemptedOutcome || '').toUpperCase() === 'ALLOW';
  addPolicyFinding(
    'GUARD-SIM-102',
    mustViolation,
    mustViolation
      ? `[${scenarioId}] MUST requirement violated by allowing known mismatch.`
      : `[${scenarioId}] MUST requirement handling is compliant.`,
    path.relative(repoRoot, simulationFixturePath),
    [
      `requirementLevel=${mustRule.requirementLevel ?? 'UNKNOWN'}`,
      `candidateMinTeamSize=${mustRule.candidateMinTeamSize ?? 'UNKNOWN'}`,
      `jobTeamSize=${mustRule.jobTeamSize ?? 'UNKNOWN'}`,
      `attemptedOutcome=${mustRule.attemptedOutcome ?? 'UNKNOWN'}`,
    ],
    mustViolation ? 'Exclude known MUST mismatches from eligibility/ranking.' : 'None.',
  );

  const unknownRule = fixture.unknownRule || {};
  const unknownViolation =
    unknownRule.jobTeamSize == null &&
    String(unknownRule.attemptedOutcome || '').toUpperCase() === 'MATCH' &&
    (!Array.isArray(unknownRule.evidenceIds) || unknownRule.evidenceIds.length === 0);
  addPolicyFinding(
    'GUARD-SIM-103',
    unknownViolation,
    unknownViolation
      ? `[${scenarioId}] UNKNOWN was coerced to MATCH without evidence.`
      : `[${scenarioId}] UNKNOWN handling remains compliant.`,
    path.relative(repoRoot, simulationFixturePath),
    [
      `jobTeamSize=${unknownRule.jobTeamSize ?? 'UNKNOWN'}`,
      `attemptedOutcome=${unknownRule.attemptedOutcome ?? 'UNKNOWN'}`,
      `evidenceIdsCount=${Array.isArray(unknownRule.evidenceIds) ? unknownRule.evidenceIds.length : 0}`,
    ],
    unknownViolation ? 'Keep UNKNOWN state unless verified evidence exists.' : 'None.',
  );

  const learningRule = fixture.learningRule || {};
  const learningViolation =
    String(learningRule.attemptedMutation || '').toUpperCase() === 'NO_TRAVEL' &&
    (!Array.isArray(learningRule.evidenceIds) || learningRule.evidenceIds.length === 0 || !learningRule.userApproval);
  addPolicyFinding(
    'GUARD-SIM-104',
    learningViolation,
    learningViolation
      ? `[${scenarioId}] Preference mutation attempted without explicit evidence/approval.`
      : `[${scenarioId}] Learning mutation governance is compliant.`,
    path.relative(repoRoot, simulationFixturePath),
    [
      `attemptedMutation=${learningRule.attemptedMutation ?? 'UNKNOWN'}`,
      `evidenceIdsCount=${Array.isArray(learningRule.evidenceIds) ? learningRule.evidenceIds.length : 0}`,
      `userApproval=${Boolean(learningRule.userApproval)}`,
    ],
    learningViolation ? 'Require explicit evidenceIds and user approval before preference mutation.' : 'None.',
  );

  const privacyRule = fixture.privacyRule || {};
  const privacyViolation = Boolean(privacyRule.isPrivate) && Boolean(privacyRule.attemptPublicSearchable) && !Boolean(privacyRule.explicitConsent);
  addPolicyFinding(
    'GUARD-SIM-105',
    privacyViolation,
    privacyViolation
      ? `[${scenarioId}] Private candidate exposure attempted without explicit consent.`
      : `[${scenarioId}] Privacy exposure handling is compliant.`,
    path.relative(repoRoot, simulationFixturePath),
    [
      `isPrivate=${Boolean(privacyRule.isPrivate)}`,
      `attemptPublicSearchable=${Boolean(privacyRule.attemptPublicSearchable)}`,
      `explicitConsent=${Boolean(privacyRule.explicitConsent)}`,
    ],
    privacyViolation ? 'Keep candidate private until explicit consent is recorded.' : 'None.',
  );

  const searchRule = fixture.searchRule || {};
  const searchViolation = Boolean(searchRule.attemptExecuteSearch) && !Boolean(searchRule.searchIntentApproval);
  addPolicyFinding(
    'GUARD-SIM-106',
    searchViolation,
    searchViolation
      ? `[${scenarioId}] Search executed without search intent approval.`
      : `[${scenarioId}] Search approval gating is compliant.`,
    path.relative(repoRoot, simulationFixturePath),
    [
      `attemptExecuteSearch=${Boolean(searchRule.attemptExecuteSearch)}`,
      `searchIntentApproval=${Boolean(searchRule.searchIntentApproval)}`,
      `hasCareerDNA=${Boolean(searchRule.hasCareerDNA)}`,
      `hasSearchIntent=${Boolean(searchRule.hasSearchIntent)}`,
    ],
    searchViolation ? 'Require explicit search intent approval prior to matching execution.' : 'None.',
  );

  return mod;
}

function checkPrivacyAudit() {
  const mod = moduleResult('privacy-audit', 'Privacy Audit');
  const srcRoot = path.join(frontendRoot, 'src');

  if (!exists(srcRoot)) {
    addFinding(mod, {
      ruleId: 'GUARD-PRV-001',
      severity: SEVERITY.HIGH,
      status: STATUS.BLOCK,
      message: 'Frontend source directory is missing.',
      evidence: ['frontend/src missing'],
      filePath: 'frontend/src',
      requiredAction: 'Restore frontend source tree before deployment.',
    });
    return mod;
  }

  const riskyFindings = [];
  for (const file of collectFiles(srcRoot)) {
    const text = readTextSafe(file);
    if (!text) {
      continue;
    }

    const hasLinkedIn = /linkedin/i.test(text);
    const hasScrape = /scrap(e|ing)/i.test(text);

    if (hasLinkedIn && hasScrape) {
      riskyFindings.push(path.relative(repoRoot, file));
    }
  }

  if (riskyFindings.length > 0) {
    addFinding(mod, {
      ruleId: 'GUARD-PRV-002',
      severity: SEVERITY.CRITICAL,
      status: STATUS.BLOCK,
      message: 'Potential LinkedIn scraping pattern detected in frontend source.',
      evidence: riskyFindings,
      filePath: riskyFindings[0],
      requiredAction: 'Remove scraping behavior and keep consented import architecture only.',
    });
  } else {
    addFinding(mod, {
      ruleId: 'GUARD-PRV-002',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'No LinkedIn scraping lexical pattern found in frontend source.',
      evidence: ['No file contains both linkedin and scrape tokens.'],
      filePath: 'frontend/src',
      requiredAction: 'None.',
    });
  }

  return mod;
}

function checkDataTruthAudit() {
  const mod = moduleResult('data-truth-audit', 'Data Truth Audit');

  const filesToCheck = [
    'MASTER_PLATFORM_AUDIT.json',
    'database/florida_facility_universe_canonical.json',
    'database/recommendation_traceability_matrix.json',
  ];

  for (const rel of filesToCheck) {
    const abs = path.join(repoRoot, rel);
    if (!exists(abs)) {
      addFinding(mod, {
        ruleId: 'GUARD-DAT-001',
        severity: SEVERITY.HIGH,
        status: STATUS.BLOCK,
        message: 'Required data truth artifact missing.',
        evidence: [rel],
        filePath: rel,
        requiredAction: 'Restore required data truth artifact.',
      });
      continue;
    }

    const payload = readJsonSafe(abs);
    if (payload === null) {
      addFinding(mod, {
        ruleId: 'GUARD-DAT-002',
        severity: SEVERITY.HIGH,
        status: STATUS.BLOCK,
        message: 'Data truth artifact is invalid JSON.',
        evidence: [rel],
        filePath: rel,
        requiredAction: 'Fix data artifact JSON integrity.',
      });
    } else {
      addFinding(mod, {
        ruleId: 'GUARD-DAT-003',
        severity: SEVERITY.LOW,
        status: STATUS.PASS,
        message: 'Data truth artifact exists and is valid JSON.',
        evidence: [rel],
        filePath: rel,
        requiredAction: 'None.',
      });
    }
  }

  return mod;
}

function checkUxOsComplianceAudit() {
  const mod = moduleResult('ux-os-compliance-audit', 'UX/OS Compliance Audit');

  const typecheck = runCommand('npm run typecheck');
  if (!typecheck.ok) {
    addFinding(mod, {
      ruleId: 'GUARD-UX-001',
      severity: SEVERITY.CRITICAL,
      status: STATUS.BLOCK,
      message: 'TypeScript typecheck failed.',
      evidence: [typecheck.stderr || typecheck.stdout || `Exit code ${typecheck.code}`],
      filePath: 'frontend/tsconfig.json',
      requiredAction: 'Resolve type errors before merge.',
    });
  } else {
    addFinding(mod, {
      ruleId: 'GUARD-UX-001',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'TypeScript typecheck passed.',
      evidence: ['npm run typecheck passed'],
      filePath: 'frontend/tsconfig.json',
      requiredAction: 'None.',
    });
  }

  const build = runCommand('npm run build');
  if (!build.ok) {
    addFinding(mod, {
      ruleId: 'GUARD-UX-002',
      severity: SEVERITY.CRITICAL,
      status: STATUS.BLOCK,
      message: 'Frontend build failed.',
      evidence: [build.stderr || build.stdout || `Exit code ${build.code}`],
      filePath: 'frontend/package.json',
      requiredAction: 'Fix build breakages before deploy.',
    });
  } else {
    addFinding(mod, {
      ruleId: 'GUARD-UX-002',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'Frontend build passed.',
      evidence: ['npm run build passed'],
      filePath: 'frontend/package.json',
      requiredAction: 'None.',
    });
  }

  return mod;
}

function checkDeploymentAudit() {
  const mod = moduleResult('deployment-audit', 'Deployment Audit');

  const nursingBoundaryPath = path.join(repoRoot, '.github', 'workflows', 'nursing-boundary.yml');
  const guardianWorkflowPath = path.join(repoRoot, '.github', 'workflows', 'optime-guardian.yml');

  const boundaryText = readTextSafe(nursingBoundaryPath) || '';
  if (!boundaryText) {
    addFinding(mod, {
      ruleId: 'GUARD-DEP-001',
      severity: SEVERITY.CRITICAL,
      status: STATUS.BLOCK,
      message: 'Primary nursing boundary workflow is missing.',
      evidence: ['.github/workflows/nursing-boundary.yml'],
      filePath: '.github/workflows/nursing-boundary.yml',
      requiredAction: 'Restore boundary workflow.',
    });
  } else {
    const needed = ['pull_request:', 'push:', 'npm run typecheck', 'npm run test:os-boundary', 'npm run build'];
    const missing = needed.filter((token) => !boundaryText.includes(token));
    if (missing.length > 0) {
      addFinding(mod, {
        ruleId: 'GUARD-DEP-002',
        severity: SEVERITY.HIGH,
        status: STATUS.BLOCK,
        message: 'Boundary workflow is missing required gate steps.',
        evidence: missing,
        filePath: '.github/workflows/nursing-boundary.yml',
        requiredAction: 'Restore required CI gate steps in boundary workflow.',
      });
    } else {
      addFinding(mod, {
        ruleId: 'GUARD-DEP-002',
        severity: SEVERITY.LOW,
        status: STATUS.PASS,
        message: 'Boundary workflow contains required CI gate steps.',
        evidence: ['Required gate steps present.'],
        filePath: '.github/workflows/nursing-boundary.yml',
        requiredAction: 'None.',
      });
    }
  }

  const guardianText = readTextSafe(guardianWorkflowPath) || '';
  if (!guardianText) {
    addFinding(mod, {
      ruleId: 'GUARD-DEP-003',
      severity: SEVERITY.HIGH,
      status: STATUS.WARN,
      message: 'Guardian workflow file not found yet.',
      evidence: ['.github/workflows/optime-guardian.yml missing'],
      filePath: '.github/workflows/optime-guardian.yml',
      requiredAction: 'Create Guardian workflow with push, PR, and hourly schedule triggers.',
    });
  } else {
    const requiredGuardianTokens = ['pull_request:', 'push:', 'schedule:', '0 * * * *'];
    const missingGuardian = requiredGuardianTokens.filter((token) => !guardianText.includes(token));
    if (missingGuardian.length > 0) {
      addFinding(mod, {
        ruleId: 'GUARD-DEP-004',
        severity: SEVERITY.HIGH,
        status: STATUS.BLOCK,
        message: 'Guardian workflow exists but is missing required enforcement triggers.',
        evidence: missingGuardian,
        filePath: '.github/workflows/optime-guardian.yml',
        requiredAction: 'Add PR, push, and hourly scheduled Guardian enforcement.',
      });
    } else {
      addFinding(mod, {
        ruleId: 'GUARD-DEP-004',
        severity: SEVERITY.LOW,
        status: STATUS.PASS,
        message: 'Guardian workflow includes PR, push, and hourly schedule triggers.',
        evidence: ['Guardian enforcement triggers found.'],
        filePath: '.github/workflows/optime-guardian.yml',
        requiredAction: 'None.',
      });
    }
  }

  return mod;
}

function checkAgentBehaviorAudit() {
  const mod = moduleResult('agent-behavior-audit', 'Agent Behavior Audit');
  const watchdogPath = path.join(repoRoot, 'scripts', 'run_supervisor_watchdog.py');
  const killSwitchPath = path.join(repoRoot, '.github', 'guardian-kill-switch.json');

  if (!exists(watchdogPath)) {
    addFinding(mod, {
      ruleId: 'GUARD-AGT-001',
      severity: SEVERITY.MEDIUM,
      status: STATUS.WARN,
      message: 'Supervisor watchdog script missing; agent runtime monitoring is degraded.',
      evidence: ['scripts/run_supervisor_watchdog.py missing'],
      filePath: 'scripts/run_supervisor_watchdog.py',
      requiredAction: 'Restore watchdog monitor script.',
    });
  } else {
    addFinding(mod, {
      ruleId: 'GUARD-AGT-001',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'Supervisor watchdog script is present.',
      evidence: ['scripts/run_supervisor_watchdog.py found'],
      filePath: 'scripts/run_supervisor_watchdog.py',
      requiredAction: 'None.',
    });
  }

  if (!exists(killSwitchPath)) {
    addFinding(mod, {
      ruleId: 'GUARD-AGT-002',
      severity: SEVERITY.HIGH,
      status: STATUS.BLOCK,
      message: 'Guardian kill switch config is missing.',
      evidence: ['.github/guardian-kill-switch.json missing'],
      filePath: '.github/guardian-kill-switch.json',
      requiredAction: 'Create kill switch config file.',
    });
    return mod;
  }

  const killSwitch = readJsonSafe(killSwitchPath);
  if (!killSwitch || typeof killSwitch !== 'object') {
    addFinding(mod, {
      ruleId: 'GUARD-AGT-003',
      severity: SEVERITY.HIGH,
      status: STATUS.BLOCK,
      message: 'Guardian kill switch config is invalid JSON.',
      evidence: ['Failed to parse .github/guardian-kill-switch.json'],
      filePath: '.github/guardian-kill-switch.json',
      requiredAction: 'Fix kill switch JSON schema.',
    });
    return mod;
  }

  if (killSwitch.manualBlock === true) {
    addFinding(mod, {
      ruleId: 'GUARD-AGT-004',
      severity: SEVERITY.CRITICAL,
      status: STATUS.BLOCK,
      message: 'Manual Guardian kill switch is active.',
      evidence: [String(killSwitch.reason || 'No reason provided')],
      filePath: '.github/guardian-kill-switch.json',
      requiredAction: 'Disable manualBlock only after resolving the active incident.',
    });
  } else {
    addFinding(mod, {
      ruleId: 'GUARD-AGT-004',
      severity: SEVERITY.LOW,
      status: STATUS.PASS,
      message: 'Manual Guardian kill switch is not active.',
      evidence: ['manualBlock: false'],
      filePath: '.github/guardian-kill-switch.json',
      requiredAction: 'None.',
    });
  }

  return mod;
}

function chooseVerdict(modules) {
  const statuses = modules.map((mod) => mod.status);
  if (statuses.includes(STATUS.BLOCK)) {
    return STATUS.BLOCK;
  }
  if (statuses.includes(STATUS.WARN)) {
    return STATUS.WARN;
  }
  return STATUS.PASS;
}

function computeFingerprint(blockFindings) {
  const normalized = blockFindings
    .map((f) => `${f.ruleId}|${f.filePath}|${f.message}`)
    .sort()
    .join('\n');

  return crypto.createHash('sha256').update(normalized, 'utf8').digest('hex').slice(0, 16);
}

function updateIncidentState(verdict, runAt, blockFindings, fingerprint) {
  ensureDir(incidentsRoot);
  const openIncidentPath = path.join(incidentsRoot, 'open-block.json');

  if (verdict === STATUS.BLOCK) {
    const current = readJsonSafe(openIncidentPath);
    const next = {
      incidentType: 'GUARDIAN_BLOCK',
      fingerprint,
      firstSeenAt: current && current.fingerprint === fingerprint ? current.firstSeenAt : runAt,
      lastSeenAt: runAt,
      unresolved: true,
      violationCount: blockFindings.length,
      ruleIds: blockFindings.map((finding) => finding.ruleId),
    };

    fs.writeFileSync(openIncidentPath, `${JSON.stringify(next, null, 2)}\n`, 'utf8');
    return next;
  }

  if (exists(openIncidentPath)) {
    const openIncident = readJsonSafe(openIncidentPath);
    const resolvedPath = path.join(incidentsRoot, 'last-resolved.json');
    const resolved = {
      ...(openIncident || {}),
      unresolved: false,
      resolvedAt: runAt,
    };
    fs.writeFileSync(resolvedPath, `${JSON.stringify(resolved, null, 2)}\n`, 'utf8');
    fs.unlinkSync(openIncidentPath);
  }

  return null;
}

function summarizeFindings(modules) {
  const all = modules.flatMap((mod) => mod.findings.map((finding) => ({ ...finding, moduleId: mod.moduleId, moduleTitle: mod.title })));
  const block = all.filter((finding) => finding.status === STATUS.BLOCK);
  const warn = all.filter((finding) => finding.status === STATUS.WARN);
  const pass = all.filter((finding) => finding.status === STATUS.PASS);

  return { all, block, warn, pass };
}

function printReport(verdict, modules, summary) {
  console.log('\\nOPTIME Guardian Modules:');
  for (const mod of modules) {
    console.log(`- ${mod.title}: ${mod.status}`);
  }

  if (summary.block.length > 0) {
    console.log('\\nBLOCK Findings:');
    for (const finding of summary.block) {
      console.log(`- [${finding.ruleId}] ${finding.message} (${finding.filePath})`);
    }
  }

  if (summary.warn.length > 0) {
    console.log('\\nWARN Findings:');
    for (const finding of summary.warn) {
      console.log(`- [${finding.ruleId}] ${finding.message} (${finding.filePath})`);
    }
  }

  console.log('');
  if (verdict === STATUS.BLOCK) {
    console.log('OPTIME GUARDIAN: BLOCKED');
    console.log('Process stopped.');
    console.log(`Violations: ${summary.block.length}`);
    return;
  }

  if (verdict === STATUS.WARN) {
    console.log('OPTIME GUARDIAN: WARN');
    console.log(`Violations: ${summary.warn.length}`);
    return;
  }

  console.log('OPTIME GUARDIAN: PASS');
}

function writeArtifacts(payload) {
  ensureDir(reportsRoot);
  fs.writeFileSync(path.join(reportsRoot, 'latest.json'), `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  fs.writeFileSync(path.join(reportsRoot, 'status.json'), `${JSON.stringify(payload.status, null, 2)}\n`, 'utf8');
}

function main() {
  const runAt = new Date().toISOString();

  const modules = simulationOnly
    ? [
        checkSimulationPolicyAudit(),
        checkAgentBehaviorAudit(),
      ]
    : [
        checkConstitutionAudit(),
        checkDecisionSymmetryAudit(),
        checkEvidenceAndProvenanceAudit(),
        checkLearningSafetyAudit(),
        checkSimulationPolicyAudit(),
        checkPrivacyAudit(),
        checkDataTruthAudit(),
        checkUxOsComplianceAudit(),
        checkDeploymentAudit(),
        checkAgentBehaviorAudit(),
      ];

  const verdict = chooseVerdict(modules);
  const summary = summarizeFindings(modules);
  const fingerprint = computeFingerprint(summary.block);
  const incident = updateIncidentState(verdict, runAt, summary.block, fingerprint);

  const statusPayload = {
    runAt,
    verdict,
    violationCount: summary.block.length,
    warningCount: summary.warn.length,
    fingerprint,
    agentExecutionAllowed: verdict !== STATUS.BLOCK,
    gate: verdict === STATUS.BLOCK ? 'STOP' : 'GO',
    requiredCheck: 'optime-guardian',
    incident,
  };

  const artifactPayload = {
    schemaVersion: '1.0.0',
    runAt,
    verdict,
    modules,
    findings: summary.all,
    status: statusPayload,
  };

  writeArtifacts(artifactPayload);
  printReport(verdict, modules, summary);

  process.exit(verdict === STATUS.BLOCK ? 1 : 0);
}

main();
