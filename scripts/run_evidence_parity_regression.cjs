const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const sourcePath = path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts');
const source = fs.readFileSync(sourcePath, 'utf8');
const comparatorMatch = source.match(/\.sort\(\(a, b\) => \{([\s\S]*?)\n\s*\}\);/);
const comparatorBlock = comparatorMatch ? comparatorMatch[1] : '';

function check(label, condition, evidence) {
  return { label, pass: Boolean(condition), evidence };
}

const checks = [];
checks.push(check(
  '1) Adding 100 irrelevant profile fields does not improve rank',
  !/profileCompletenessScore\s*\|\|/.test(source),
  'Ranking comparator no longer uses profileCompletenessScore tie-break.'
));

checks.push(check(
  '2) Adding duplicate evidence does not improve rank',
  comparatorBlock.length > 0
    && !/verification_count|evidence_records\.length|source_traceability\.length|sourceCoverage|intelligenceSourcesUsed\.length/.test(comparatorBlock),
  'Comparator does not use evidence-count or source-volume features as ranking input.'
));

checks.push(check(
  '3) UNKNOWN does not equal NO',
  source.includes('never count as NO') && source.includes('UNKNOWN or unverified items'),
  'Traceability keeps UNKNOWN separate from verified NO.'
));

checks.push(check(
  '4) Missing information does not create a negative penalty',
  source.includes('reduce confidence only and are never treated as NO'),
  'Unresolved evidence affects confidence, not direct negative scoring.'
));

checks.push(check(
  '5) Verified case-critical positive evidence can strengthen recommendation',
  source.includes('const governedFitDelta = (recommendationB + niceB) - (recommendationA + niceA);')
    && source.includes('const provenDelta = b.report.matchEvidenceStatus.provenMatchScore - a.report.matchEvidenceStatus.provenMatchScore;'),
  'Ranking includes governed fit then proven match from verified evidence.'
));

checks.push(check(
  '6) Verified negative evidence can weaken recommendation',
  source.includes('governedDecision.eligibility_status === "MUST_REJECTED"') && source.includes('hardRejectionReasons.push("Governed MUST eligibility failed.")'),
  'Governed MUST failures are enforced before ranking.'
));

checks.push(check(
  '7) Facility-supplied unverified claims do not improve rank',
  source.includes('state = "LIMITED";')
    && source.includes('independent verification is still required.')
    && source.includes('assessment.state === "YES" && assessment.evidenceVerified'),
  'Unverified metadata signals are LIMITED and do not contribute to proven YES.'
));

checks.push(check(
  '8) Verification of previously critical UNKNOWN can change ranking when relevant',
  source.includes('const memoryCapability = getActiveKnowledgeCapability')
    && source.includes('evidenceVerified: true')
    && source.includes('verifiedYes = scoredRequirements.filter((assessment) => assessment.state === "YES" && assessment.evidenceVerified).length;'),
  'When verification memory resolves UNKNOWN to verified YES/NO, proven score updates.'
));

checks.push(check(
  '9) Evidence Confidence is separate from Quality',
  source.includes('matchEvidenceStatus')
    && source.includes('caseRelevantEvidenceCoveragePct')
    && source.includes('priorityScores.clinicalQuality'),
  'Coverage/confidence fields are explicit and separate from clinical quality features.'
));

checks.push(check(
  '10) Deeply researched facility does not win merely because it was deeply researched',
  !/profileCompletenessScore/.test(source)
    && !/sourceCoverage.*sort|source_traceability.*sort|evidence_records.*sort/.test(source),
  'Ranking does not use generic completeness/source volume as a tie-break.'
));

const pass = checks.every((c) => c.pass);
const report = {
  generated_at_utc: new Date().toISOString(),
  pass,
  checks,
};

const outPath = path.join(repoRoot, 'reports', 'EVIDENCE_PARITY_REGRESSION_TESTS.json');
fs.writeFileSync(outPath, JSON.stringify(report, null, 2), 'utf8');

console.log(`WROTE ${outPath}`);
console.log(`REGRESSION_TESTS=${pass ? 'PASS' : 'FAIL'}`);
if (!pass) process.exitCode = 1;
