const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { resolveCanonicalPython } = require('./lib/python_runtime.cjs');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));
const {
  createVerificationInbox,
  applyProviderVerificationAnswers,
} = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'verification-inbox.ts'));

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
      'Resident age 80.',
      'History of stroke.',
      'Uses walker.',
      'Requires 24/7 support.',
      'Requires gluten-free meals.',
      'Prefers movies and music programs.',
      'Budget 12000 monthly.',
      'Preferred location Miami.',
    ].join(' '),
    humanIntelligenceV2: {
      ...base.humanIntelligenceV2,
      foodProfile: {
        dietaryPreferences: ['Gluten-free'],
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
        familyVisitExpectation: 'Weekly',
        driveTimes: {
          normal: '25',
          rushHour: '40',
          emergency: '20',
        },
      },
    },
  };
}

function toSimulationFacilityList() {
  const backendFacilities = simulationHelpers.loadBackendFacilities();
  return backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));
}

function runPythonSnippet(code, args = []) {
  const pythonPath = resolveCanonicalPython(repoRoot);
  const result = spawnSync(pythonPath, ['-c', code, ...args], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error(`Python execution failed: ${result.stderr || result.stdout}`.trim());
  }

  return (result.stdout || '').trim();
}

function seedFamilyNoReports(facilityId, capabilityKey, count = 3) {
  const code = [
    'import sys',
    'from datetime import datetime, timedelta, timezone',
    'sys.path.insert(0, r"' + path.join(repoRoot, 'backend').replace(/\\/g, '\\\\') + '")',
    'from app.database import SessionLocal',
    'from app.models.facility import FacilityVerificationRequest, FacilityVerificationResponse, AnswerState',
    'facility_id = int(sys.argv[1])',
    'capability_key = sys.argv[2]',
    'count = int(sys.argv[3])',
    'db = SessionLocal()',
    'try:',
    '  req = FacilityVerificationRequest(facility_id=facility_id, channel="family_feedback", status="answered", subject="family report", body="family feedback")',
    '  db.add(req)',
    '  db.flush()',
    '  now = datetime.now(timezone.utc)',
    '  for _ in range(count):',
    '    db.add(FacilityVerificationResponse(request_id=req.id, facility_id=facility_id, capability=capability_key, value=AnswerState.NO, source="FAMILY_REPORT", verified_at=now, expires_at=now + timedelta(days=180), confidence=70.0, notes="seeded family report"))',
    '  db.commit()',
    'finally:',
    '  db.close()',
  ].join('\n');

  runPythonSnippet(code, [String(facilityId), String(capabilityKey), String(count)]);
}

function persistProviderAnswers(facilityId, answers, requestSubject, requestBody) {
  const payload = {
    facility_id: facilityId,
    answers,
    request_subject: requestSubject,
    request_body: requestBody,
  };

  const code = [
    'import json, sys',
    'sys.path.insert(0, r"' + path.join(repoRoot, 'backend').replace(/\\/g, '\\\\') + '")',
    'from app.database import SessionLocal',
    'from app.services.facility_memory_persistence import apply_provider_verification_answers, facility_memory_overlay',
    'payload = json.loads(sys.argv[1])',
    'db = SessionLocal()',
    'try:',
    '  result = apply_provider_verification_answers(db=db, facility_id=int(payload["facility_id"]), answers=payload["answers"], verified_by_user_id=1, verification_method="provider_portal_form", request_subject=payload.get("request_subject"), request_body=payload.get("request_body"))',
    '  overlay = facility_memory_overlay(db, int(payload["facility_id"]))',
    '  print(json.dumps({"result": result, "overlay": overlay}))',
    'finally:',
    '  db.close()',
  ].join('\n');

  return JSON.parse(runPythonSnippet(code, [JSON.stringify(payload)]));
}

function scoreProviderAnswer(question) {
  const text = String(question || '').toLowerCase();
  if (/gluten|diet|meal|movie|music|walker|wheelchair|24\/7|nursing|therapy|continuum/.test(text)) {
    return 'YES';
  }
  return 'LIMITED';
}

function main() {
  const state = buildScenarioState();
  const initialFacilities = toSimulationFacilityList();
  const initialOutput = runOptimeV2Engine(initialFacilities, state);

  if (initialOutput.accepted.length === 0) {
    throw new Error('No accepted recommendations produced for provider ecosystem simulation.');
  }

  const top = initialOutput.accepted[0];
  const clinical = top.report.audit.clinicalReasoning;
  const verificationRequest = top.report.audit.verificationRequest;
  const initialUnknownCount = verificationRequest.unknownCount;
  const initialConfidence = verificationRequest.confidenceScore;

  const inbox = createVerificationInbox(initialOutput);
  const topInbox = inbox.find((item) => item.facility_id === top.facility.id) || null;

  let providerIntegration = null;
  let persistenceResult = null;
  let finalUnknownCount = initialUnknownCount;
  let finalConfidence = initialConfidence;
  let updatedCapabilitiesCount = 0;
  let conflictEnginePass = false;

  if (topInbox && topInbox.questions.length > 0) {
    const answers = {};
    topInbox.questions.forEach((question) => {
      answers[question.question] = scoreProviderAnswer(question.question);
    });

    providerIntegration = applyProviderVerificationAnswers({
      facility: top.facility,
      state,
      checklist: top.report.audit.verificationChecklist,
      answers,
      verifiedAt: new Date().toISOString(),
      expiresInDays: 90,
    });

    const memory = providerIntegration.memorySnapshot;
    const providerPortalCapabilities = memory
      ? Object.values(memory.capabilities)
        .filter((entry) => entry.source === 'PROVIDER_PORTAL')
        .map((entry) => ({ capability_key: entry.key, value: entry.state, source: entry.source }))
      : [];

    updatedCapabilitiesCount = providerPortalCapabilities.length;

    // Seed family NO reports for conflict detection rule before provider YES persistence.
    seedFamilyNoReports(top.facility.id, 'speech_therapy', 3);

    persistenceResult = persistProviderAnswers(
      top.facility.id,
      providerPortalCapabilities,
      verificationRequest.subject,
      verificationRequest.body,
    );

    const rerunFacilities = toSimulationFacilityList();
    const rerunOutput = runOptimeV2Engine(rerunFacilities, state);
    const rerunTop = rerunOutput.accepted.find((item) => item.facility.id === top.facility.id) || rerunOutput.accepted[0];
    finalUnknownCount = rerunTop.report.audit.verificationRequest.unknownCount;
    finalConfidence = rerunTop.report.audit.verificationRequest.confidenceScore;

    const conflictEntry = (persistenceResult.overlay.capabilities || []).find((item) => item.capability_key === 'speech_therapy');
    conflictEnginePass = Boolean(conflictEntry && conflictEntry.status === 'CONFLICT_REVIEW_REQUIRED');
  }

  const lines = [];
  lines.push('# Facility Memory Persistence Simulation');
  lines.push('');
  lines.push('## Scenario');
  lines.push('');
  lines.push('- Resident age: 80');
  lines.push('- Clinical context: stroke history, walker, requires 24/7 support');
  lines.push('- Lifestyle: movies, music');
  lines.push('- Dietary: gluten free');
  lines.push('- Budget: $12,000/month');
  lines.push('- Location: Miami');
  lines.push('');
  lines.push('## Top Recommendation');
  lines.push('');
  lines.push(`- Community: **${top.facility.name}**`);
  lines.push(`- Match score: **${top.report.finalMatchScore}**`);
  lines.push(`- Verification readiness: **${top.report.audit.verificationReadinessScore}**`);
  lines.push('');

  lines.push('## Verified Capabilities');
  lines.push('');
  if (clinical.verifiedCapabilities.length > 0) {
    clinical.verifiedCapabilities.forEach((item) => lines.push(`- ${item}`));
  } else {
    lines.push('- None currently verified.');
  }
  lines.push('');

  lines.push('## Unknown Capabilities');
  lines.push('');
  if (clinical.unknownCapabilities.length > 0) {
    clinical.unknownCapabilities.forEach((item) => lines.push(`- ${item}`));
  } else {
    lines.push('- None.');
  }
  lines.push('');

  lines.push('## Verification Questions');
  lines.push('');
  if (clinical.questionsForFacility.length > 0) {
    clinical.questionsForFacility.forEach((question) => lines.push(`- ${question}`));
  } else {
    lines.push('- None (no open unknown capabilities).');
  }
  lines.push('');

  lines.push('## Narrative Output');
  lines.push('');
  lines.push('```text');
  lines.push('Why OPTIME selected this community');
  lines.push(clinical.whyThisCommunity || '');
  lines.push('');
  lines.push('Medical Match');
  lines.push(clinical.medicalMatch || '');
  lines.push('');
  lines.push('Lifestyle Match');
  lines.push(clinical.lifestyleMatch || '');
  lines.push('');
  lines.push('Dietary Match');
  lines.push(clinical.dietaryMatch || '');
  lines.push('');
  lines.push('Social Match');
  lines.push(clinical.socialMatch || '');
  lines.push('');
  lines.push('Future Care Match');
  lines.push(clinical.futureCareMatch || '');
  lines.push('');
  lines.push('Verification Needed');
  lines.push(clinical.verificationNeeded || '');
  lines.push('```');
  lines.push('');

  lines.push('## Provider Portal Integration');
  lines.push('');
  lines.push('- Inbox generation:');
  lines.push(`  - Total provider inbox items: **${inbox.length}**`);
  lines.push(`  - Top facility inbox status: **${topInbox ? topInbox.status : 'NONE'}**`);
  lines.push(`  - Resident info shared: **${topInbox ? String(topInbox.privacy.resident_info_shared) : 'false'}**`);
  lines.push('');
  lines.push('- Anonymous verification request payload (capability-only):');
  lines.push('');
  lines.push(`  - Subject: ${verificationRequest.subject}`);
  lines.push('');
  lines.push('```text');
  lines.push(verificationRequest.body);
  lines.push('```');
  lines.push('');

  if (providerIntegration) {
    lines.push('- Provider answers applied through PROVIDER_PORTAL: **YES**');
    lines.push(`- Initial unknown count: **${initialUnknownCount}**`);
    lines.push(`- Final unknown count: **${finalUnknownCount}**`);
    lines.push(`- Initial confidence: **${initialConfidence}**`);
    lines.push(`- Final confidence: **${finalConfidence}**`);
    lines.push(`- Updated capabilities persisted: **${updatedCapabilitiesCount}**`);

    if (persistenceResult) {
      lines.push(`- Persisted answers: **${persistenceResult.result.persisted_answers}**`);
      lines.push(`- Conflict records: **${persistenceResult.result.conflict_records}**`);
      lines.push(`- Conflict engine status: **${conflictEnginePass ? 'PASS' : 'FAIL'}**`);
    }

    lines.push('');
    lines.push('## Simulation Assertions');
    lines.push('');
    lines.push(`- UNKNOWN decreases after persistence: **${finalUnknownCount < initialUnknownCount ? 'PASS' : 'FAIL'}**`);
    lines.push(`- Confidence increases after persistence: **${finalConfidence > initialConfidence ? 'PASS' : 'FAIL'}**`);
    lines.push(`- Conflict detection rule enforced: **${conflictEnginePass ? 'PASS' : 'FAIL'}**`);
  } else {
    lines.push('- Provider answers applied through PROVIDER_PORTAL: **NO** (no unknown questions for top facility).');
  }

  const reportPath = path.join(repoRoot, 'reports', 'facility_memory_persistence_simulation.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  // Keep legacy report path updated for existing validations.
  const legacyPath = path.join(repoRoot, 'reports', 'provider_ecosystem_simulation.md');
  fs.writeFileSync(legacyPath, lines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`Wrote ${legacyPath}`);
  console.log(`TOP_MATCH=${top.facility.name}`);
  console.log(`INITIAL_UNKNOWN_COUNT=${initialUnknownCount}`);
  console.log(`FINAL_UNKNOWN_COUNT=${finalUnknownCount}`);
  console.log(`INITIAL_CONFIDENCE=${initialConfidence}`);
  console.log(`FINAL_CONFIDENCE=${finalConfidence}`);
  console.log(`UPDATED_CAPABILITIES_COUNT=${updatedCapabilitiesCount}`);
  console.log(`CONFLICT_ENGINE_PASS=${conflictEnginePass ? 'PASS' : 'FAIL'}`);
}

main();
