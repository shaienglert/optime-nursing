const fs = require('fs');

const interview = fs.readFileSync('frontend/src/app/adaptive-interview/page.tsx', 'utf8');
const resultsPage = fs.readFileSync('frontend/src/app/results/page.tsx', 'utf8');
const simpleResults = fs.readFileSync('frontend/src/app/results/simple-results-page-client.tsx', 'utf8');

for (const token of ['adaptive_questions', 'answer_options', 'adaptiveSignals', 'existingAnswerFor', 'autoResolved', 'canonicalizeAdaptiveFact']) {
  if (!interview.includes(token)) throw new Error(`Nursing AI-owned interview invariant missing: ${token}`);
}

for (const forbidden of ['community_size_preference', 'social_interaction_need_after_loss', 'social_interaction_preference', 'move_participation', 'fallbackOptions(']) {
  if (interview.includes(forbidden)) throw new Error(`Legacy hard-coded adaptive interview behavior remains: ${forbidden}`);
}

if (!interview.includes('question?.answer_options || []')) throw new Error('Answer options must come from governed runtime only.');
if (!interview.includes('router.replace(destination)')) throw new Error('READY must leave the clarification surface without creating a redundant interview history step.');
if (!interview.includes('We use everything you already told us.')) throw new Error('Interview must disclose the no-reask contract to the user.');

if (!resultsPage.includes('SimpleResultsPageClient')) throw new Error('Senior-readable results summary must be the default results surface.');
for (const token of ['Meets verified must-haves', 'What we still want to confirm', 'See detailed comparison', 'Other promising places we are still checking']) {
  if (!simpleResults.includes(token)) throw new Error(`Senior-readable result contract missing: ${token}`);
}
if (!simpleResults.includes('eligibility_status === "ELIGIBLE"')) throw new Error('Only verified-eligible facilities may be presented as leading recommendations.');
if (!simpleResults.includes('text-xl') || !simpleResults.includes('text-2xl')) throw new Error('Primary result copy must use senior-readable typography.');

console.log('Nursing AI-owned no-reask + senior-readable UI validation: PASS');
