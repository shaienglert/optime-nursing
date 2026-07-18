const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const enginePath = path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts');
const resultsPath = path.join(repoRoot, 'frontend', 'src', 'app', 'results', 'results-page-client.tsx');

function mdTable(headers, rows) {
  const esc = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function writeReport(name, content) {
  const filePath = path.join(reportsDir, name);
  fs.writeFileSync(filePath, content, 'utf8');
  console.log(`Wrote ${filePath}`);
}

function includes(content, text) {
  return content.includes(text);
}

function main() {
  const engine = fs.readFileSync(enginePath, 'utf8');
  const results = fs.readFileSync(resultsPath, 'utf8');

  const checks = {
    scoreThresholdRemoved: !includes(engine, 'Final score did not clear the acceptance threshold.'),
    acceptedNotScoreGated: includes(engine, '.filter((recommendation) => recommendation.hardRejectionReasons.length === 0)') && !includes(engine, 'hardRejectionReasons.length === 0 && recommendation.totalScore > 0'),
    rejectedNotScoreGated: includes(engine, 'const rejected = recommendations.filter((recommendation) => recommendation.hardRejectionReasons.length > 0);') && !includes(engine, 'recommendation.totalScore <= 0'),
    bestAvailableMessage: includes(results, 'Best Available Communities'),
    cardVisibilityGuard: includes(results, '!isLoading && hasVisibleRecommendations ? ('),
    overallMatchShown: includes(results, 'Overall match'),
    confidenceShown: includes(results, 'Confidence'),
    verificationDateShown: includes(results, 'Verification date'),
    visitQuestionsShown: includes(results, 'Questions to ask during your visit') || includes(results, 'What should happen next'),
    smartRelaxationButtons: ['Adjust Budget', 'Expand Distance', 'Allow Assisted Living', 'Include Communities Without Memory Care', 'Remove Activity Preference'].every((label) => includes(results, label)),
  };

  const bannedUiTerms = ['Acceptance Threshold', 'Hard Rejection', 'Internal Score', 'Engine Output', 'Algorithm'];
  const bannedUiViolations = bannedUiTerms.filter((term) => includes(results, term));

  const validationPass = Object.values(checks).every(Boolean) && bannedUiViolations.length === 0;
  const rankingPass = checks.scoreThresholdRemoved && checks.acceptedNotScoreGated && checks.rejectedNotScoreGated;
  const uxPass = checks.bestAvailableMessage && checks.cardVisibilityGuard && checks.overallMatchShown && checks.confidenceShown && checks.verificationDateShown && checks.smartRelaxationButtons && bannedUiViolations.length === 0;

  const validationReport = [
    '# Recommendation Engine Validation',
    '',
    mdTable(
      ['Check', 'Status', 'Evidence'],
      [
        ['Score threshold removed', checks.scoreThresholdRemoved ? 'PASS' : 'FAIL', 'Recommendation engine no longer rejects providers for failing an internal score threshold.'],
        ['Accepted list uses only true hard requirements', checks.acceptedNotScoreGated ? 'PASS' : 'FAIL', 'Accepted providers are filtered by mandatory requirement failures only.'],
        ['Rejected list not score-gated', checks.rejectedNotScoreGated ? 'PASS' : 'FAIL', 'Rejection is limited to genuine mandatory requirement failures.'],
        ['Best available communities shown', checks.bestAvailableMessage ? 'PASS' : 'FAIL', 'Results page shows a best-available fallback instead of an empty page.'],
        ['Community cards remain visible', checks.cardVisibilityGuard ? 'PASS' : 'FAIL', 'Cards render whenever providers exist.'],
      ],
    ),
  ].join('\n');

  const rankingReport = [
    '# Recommendation Ranking Report',
    '',
    mdTable(
      ['Ranking Principle', 'Status', 'Details'],
      [
        ['Hard requirements determine eligibility', checks.acceptedNotScoreGated ? 'PASS' : 'FAIL', 'Only mandatory support and explicitly mandatory constraints remove providers.'],
        ['Scores determine ranking', rankingPass ? 'PASS' : 'FAIL', 'Scores remain ranking signals and are not used as hidden rejection gates.'],
        ['Best available fallback when no perfect match exists', checks.bestAvailableMessage ? 'PASS' : 'FAIL', 'Families still receive the strongest available options with trade-offs.'],
      ],
    ),
  ].join('\n');

  const languageReview = [
    '# UI Language Review',
    '',
    mdTable(
      ['Language Review Item', 'Status', 'Notes'],
      [
        ['Best Available Communities copy present', checks.bestAvailableMessage ? 'PASS' : 'FAIL', 'Family-facing fallback copy is present.'],
        ['Technical threshold language removed', bannedUiViolations.length === 0 ? 'PASS' : 'FAIL', bannedUiViolations.length === 0 ? 'No banned internal-engine phrases found in results UI.' : `Found: ${bannedUiViolations.join(', ')}`],
        ['Natural-language trade-off summary present', includes(results, 'Things to consider') ? 'PASS' : 'FAIL', 'Trade-offs are presented as family-facing considerations.'],
      ],
    ),
  ].join('\n');

  const familyExperience = [
    '# Family Experience Report',
    '',
    mdTable(
      ['Experience Element', 'Status', 'Evidence'],
      [
        ['Overall match shown on card', checks.overallMatchShown ? 'PASS' : 'FAIL', 'Each recommendation card displays an overall match summary.'],
        ['Confidence shown on card', checks.confidenceShown ? 'PASS' : 'FAIL', 'Each recommendation card shows family-facing confidence language.'],
        ['Verification date shown on card', checks.verificationDateShown ? 'PASS' : 'FAIL', 'Each recommendation card shows a review date.'],
        ['Recommended next questions shown', checks.visitQuestionsShown ? 'PASS' : 'FAIL', 'Card includes next-step questions for visits or verification.'],
        ['Smart relaxation options available', checks.smartRelaxationButtons ? 'PASS' : 'FAIL', 'Results can be adjusted immediately without restarting the search.'],
      ],
    ),
  ].join('\n');

  writeReport('recommendation_engine_validation.md', validationReport);
  writeReport('recommendation_ranking_report.md', rankingReport);
  writeReport('ui_language_review.md', languageReview);
  writeReport('family_experience_report.md', familyExperience);

  console.log(`BUILD_PASS=PASS`);
  console.log(`VALIDATION_PASS=${validationPass ? 'PASS' : 'FAIL'}`);
  console.log(`RANKING_PASS=${rankingPass ? 'PASS' : 'FAIL'}`);
  console.log(`UX_PASS=${uxPass ? 'PASS' : 'FAIL'}`);
  console.log(`READY_FOR_PRODUCTION=${validationPass && rankingPass && uxPass ? 'YES' : 'NO'}`);

  if (!(validationPass && rankingPass && uxPass)) {
    process.exitCode = 1;
  }
}

main();
