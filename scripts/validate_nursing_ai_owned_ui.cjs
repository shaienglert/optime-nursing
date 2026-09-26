const fs = require('fs');

const interview = fs.readFileSync('frontend/src/app/adaptive-interview/page.tsx', 'utf8');
const intake = fs.readFileSync('frontend/src/components/intake/structured-intake.tsx', 'utf8');
const intakeQuestions = fs.readFileSync('frontend/src/lib/intake-questions.ts', 'utf8');
const intakeContract = `${intake}\n${intakeQuestions}`;
const confirmation = fs.readFileSync('frontend/src/app/intake-confirmation/page.tsx', 'utf8');
const resultsPage = fs.readFileSync('frontend/src/app/results/page.tsx', 'utf8');
const simpleResults = fs.readFileSync('frontend/src/app/results/simple-results-page-client.tsx', 'utf8');
const adaptiveAnswer = fs.readFileSync('frontend/src/lib/adaptive-answer.ts', 'utf8');

for (const token of ['adaptive_questions', 'answer_options', 'applyAdaptiveAnswer', 'context.canonical.system === "BLOCKED"', 'context.canonical.client === "COMPLETE"']) {
  if (!interview.includes(token)) throw new Error(`Nursing AI-owned interview invariant missing: ${token}`);
}
for (const token of ['adaptiveSignals', 'canonicalizeAdaptiveFact', 'clientSummaryConfirmed: false']) {
  if (!adaptiveAnswer.includes(token)) throw new Error(`Shared adaptive answer invariant missing: ${token}`);
}
if (!simpleResults.includes('applyAdaptiveAnswer')) throw new Error('Results follow-up must use shared answer persistence.');

for (const forbidden of ['community_size_preference', 'social_interaction_need_after_loss', 'social_interaction_preference', 'move_participation', 'fallbackOptions(', 'existingAnswerFor', 'autoResolved']) {
  if (interview.includes(forbidden)) throw new Error(`Legacy hard-coded adaptive interview behavior remains: ${forbidden}`);
}

for (const token of ['hasUnresolvedSemanticConflict(nested?.semantic_ai?.result?.statements)', 'context.canonical.client === "COMPLETE" && !context.hasConflict']) {
  if (!interview.includes(token)) throw new Error(`Server-reported semantic conflict guard missing: ${token}`);
}

if (!interview.includes('question?.answer_options || []')) throw new Error('Answer options must come from governed runtime only.');
if (!interview.includes('router.replace(`/intake-confirmation?next=')) throw new Error('READY must move to client confirmation before results.');
if (!interview.includes('questionnaireCompletion?.mandatoryComplete') || !interview.includes('conditionalFollowUpsComplete')) throw new Error('Adaptive interview must reject an incomplete structured questionnaire.');
if (!interview.includes('I’ll use everything you’ve already told me, so I won’t make you repeat yourself.')) throw new Error('Interview must disclose the no-reask contract to the user.');

for (const token of ['medicalCareProfile', 'moveLossConcerns', 'parkingRequirement', 'clientSummaryConfirmed: false', 'Continue our conversation']) {
  if (!intakeContract.includes(token)) throw new Error(`Mandatory structured intake contract missing: ${token}`);
}
for (const token of ['Please confirm what OOmnik understood.', 'clientSummaryConfirmed: true', 'I confirm—show recommendations']) {
  if (!confirmation.includes(token)) throw new Error(`Client confirmation contract missing: ${token}`);
}

if (!resultsPage.includes('SimpleResultsPageClient')) throw new Error('Senior-readable results summary must be the default results surface.');
for (const token of ['Meets verified must-haves', 'What gives me pause', 'See detailed comparison', 'Other promising places we are still checking']) {
  if (!simpleResults.includes(token)) throw new Error(`Senior-readable result contract missing: ${token}`);
}
const eligibility = fs.readFileSync('frontend/src/lib/recommendation-eligibility.ts', 'utf8');
const detailedResults = fs.readFileSync('frontend/src/app/results/results-page-client.tsx', 'utf8');
if (!simpleResults.includes('.filter(isFinalRecommendation)') || !detailedResults.includes('.filter(isFinalRecommendation)')
    || !eligibility.includes('must_eligibility === "MUST_ELIGIBLE"') || !eligibility.includes('eligibility_status === "ELIGIBLE"')) {
  throw new Error('Both result views must use the canonical eligibility gate before presenting final recommendations.');
}
if (!simpleResults.includes('questionnaireCompletion.clientSummaryConfirmed')) throw new Error('Results must reject an unconfirmed client summary.');
if (!simpleResults.includes('text-xl') || !simpleResults.includes('text-2xl')) throw new Error('Primary result copy must use senior-readable typography.');

console.log('Nursing mandatory intake + AI clarification + client confirmation + senior-readable UI validation: PASS');
