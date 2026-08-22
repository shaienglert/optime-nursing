const fs=require('fs');
const interview=fs.readFileSync('frontend/src/app/adaptive-interview/page.tsx','utf8');
const results=fs.readFileSync('frontend/src/app/results/page.tsx','utf8');
for(const token of ['adaptive_questions','answer_options','adaptiveSignals','>Back<','>Edit<','Start over','HISTORY_STORAGE_KEY','review=1','Change decision answers']){
  if(!(interview+results).includes(token)) throw new Error(`Nursing AI-owned UI invariant missing: ${token}`);
}
for(const forbidden of ['community_size_preference','social_interaction_need_after_loss','social_interaction_preference','move_participation','fallbackOptions(']){
  if(interview.includes(forbidden)) throw new Error(`Legacy hard-coded adaptive interview behavior remains: ${forbidden}`);
}
if(!interview.includes('question?.answer_options || []')) throw new Error('Answer options must come from governed runtime only.');
if(!interview.includes('router.push(destination)')) throw new Error('Results navigation must preserve a browser-back path to the interview.');
console.log('Nursing AI-owned adaptive UI validation: PASS');
