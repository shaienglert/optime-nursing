const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
// Synthetic reproduction, not the user's complete questionnaire:
// known dimensions: independent woman, anywhere in Las Vegas Valley, $6500.
// Remaining required choices below are explicit test assumptions.
const answers = {
 relationship: 'Mom', ageGroup: '80-84',
 referenceAddress: 'Anywhere in the Las Vegas Valley',
 assistance: ['Fully independent'], memoryStatus: 'No',
 hasOngoingMedicalNeeds: 'No', recentHospitalization: 'No',
 medicaidStatus: 'Not sure', budget: 6500, moveTiming: 'Not sure',
 moveAttitude: 'Not sure', socialFrequency: 'Occasionally',
 communityStyle: 'No preference', activities: ['Music'], activityImportance: 'Preference',
 nearbyPlaces: ['Nothing in particular'], personalDestinationLabel: 'No specific destination',
 moveLossConcerns: ['Independence'], otherInterests: '',
 language: 'English', dietary: [], religiousCommunity: 'No',
 petOwnershipImportance: 'Not sure', abilityToLeaveIndependently: 'Yes',
 parkingRequirement: 'Not sure', continuum: 'Not important',
 careSearchApproach: 'Show me both approaches',
};
test.use({ screenshot: 'only-on-failure', trace: 'retain-on-failure', video: 'retain-on-failure' });
test('production independent woman anywhere Las Vegas $6500', async ({ page }, testInfo) => {
 test.setTimeout(480000); page.setDefaultTimeout(15000);
 const dir = testInfo.outputPath('diagnostics'); fs.mkdirSync(dir, {recursive:true});
 const responseTasks = []; const network = [];
 page.on('pageerror', e => console.log('PAGE_ERROR', e.message));
 page.on('requestfailed', r => console.log('REQUEST_FAILED', r.url(), r.failure()?.errorText));
 page.on('response', r => {
   if (!/decision-engine|intake|profile|interview|recommendation/.test(r.url()) || r.request().method() !== 'POST') return;
   const task = (async () => {
     const row = {url:r.url(),status:r.status(),request:r.request().postData()};
     try { row.body = await r.json(); } catch { row.body = (await r.text().catch(()=>'' )).slice(0,10000); }
     network.push(row); fs.writeFileSync(dir+'/network.json',JSON.stringify(network,null,2));
     console.log('PRODUCTION_API', JSON.stringify(row));
   })(); responseTasks.push(task);
 });
 try {
   await page.goto('https://optime-nursing.vercel.app/', {waitUntil:'domcontentloaded',timeout:60000});
   await page.getByRole('button',{name:'my mother',exact:true}).click();
   await expect(page.getByRole('button',{name:'80-84',exact:true})).toBeVisible({timeout:15000});
   await page.getByRole('button',{name:'80-84',exact:true}).click();
   const asked = [];
   for (let i=0;i<65;i++) {
     if (await page.getByText('Yes — this reflects what I told Oomnik.',{exact:true}).isVisible()) break;
     const heading = page.locator('main h1[data-question-id]');
     await expect(heading).toBeVisible();
     const id = await heading.getAttribute('data-question-id');
     const kind = await heading.getAttribute('data-question-kind');
     if (asked.includes(id)) throw new Error('Repeated intake question: '+id);
     asked.push(id); console.log('INTAKE_STEP',id,JSON.stringify(answers[id]));
     if (!Object.hasOwn(answers,id)) throw new Error('No declared synthetic answer for '+id);
     const value = answers[id];
     if (kind==='single') { await page.getByRole('button',{name:String(value),exact:true}).click(); continue; }
     if (kind==='multi') for (const v of value) await page.getByRole('button',{name:v,exact:true}).click();
     else if (kind==='number') {
       const range=page.locator('main input[type=range]');
       await range.focus();
       const min=Number(await range.getAttribute('min'));
       const step=Number(await range.getAttribute('step'))||1;
       await range.press('Home');
       for(let k=0;k<Math.round((Number(value)-min)/step);k++) await range.press('ArrowRight');
       await expect(range).toHaveValue(String(value));
     } else if (value) await page.locator('main input[type=text], main textarea').first().fill(String(value));
     await page.getByRole('button',{name:/^(Next →|See the summary →)$/}).click();
   }
   console.log('INTAKE_SUMMARY',await page.locator('main').innerText());
   await page.getByText('Yes — this reflects what I told Oomnik.',{exact:true}).click();
   await page.getByRole('button',{name:'Continue our conversation',exact:true}).click();
   for(let i=0;i<12;i++) {
     const final=page.getByRole('button',{name:/I confirm.*show recommendations/i});
     const answer=page.getByLabel('Your answer');
     const review=page.getByRole('button',{name:'Continue our conversation',exact:true});
     let phase='';
     await expect.poll(async()=>{
       if (/results/.test(page.url())) return phase='RESULTS';
       if(await final.isVisible() && await final.isEnabled()) return phase='FINAL';
       if(await answer.isVisible() && await answer.isEnabled()) return phase='ANSWER';
       if(await review.isVisible() && await review.isEnabled()) return phase='REVIEW';
       if(await page.getByRole('button',{name:'Try again',exact:true}).isVisible()) return phase='ERROR';
       return phase='';
     },{timeout:90000}).not.toBe('');
     console.log('INTERVIEW_SCREEN',phase,await page.locator('main').innerText());
     if(phase==='RESULTS') break;
     if(phase==='ERROR') throw new Error('Production interview error');
     if(phase==='FINAL') { await final.click(); await expect(page).toHaveURL(/results/,{timeout:60000}); break; }
     if(phase==='REVIEW') { await review.click(); continue; }
     await answer.fill('Use the confirmed questionnaire facts. Fully independent woman, anywhere in the Las Vegas Valley, total monthly budget $6500. No additional mandatory facility requirement beyond the confirmed questionnaire. No preference on additional amenities.');
     await page.getByRole('button',{name:'Continue',exact:true}).click();
   }
   await expect(page).toHaveURL(/results/,{timeout:60000});
   await expect(page.getByText('OOmnik results',{exact:true})).toBeVisible({timeout:120000});
   await Promise.allSettled(responseTasks);
   console.log('FINAL_RESULTS',await page.locator('main').innerText());
 } finally {
   await Promise.allSettled(responseTasks);
   fs.writeFileSync(dir+'/screen.txt',await page.locator('main').innerText().catch(()=> 'No main'));
   fs.writeFileSync(dir+'/answers.json',JSON.stringify(answers,null,2));
   await page.screenshot({path:dir+'/screen.png',fullPage:true});
   console.log('FINAL_URL',page.url());
 }
});
