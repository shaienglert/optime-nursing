import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const OUT = path.resolve('database/ahca_browser_extract');
await fs.mkdir(OUT, { recursive: true });

const targets = [
  { key: 'nursing_home', url: 'https://quality.healthfinder.fl.gov/Facility-Provider/Nursing-Home?type=0' },
  { key: 'assisted_living', url: 'https://quality.healthfinder.fl.gov/Facility-Provider/ALF?type=1' },
  { key: 'adult_family_care', url: 'https://quality.healthfinder.fl.gov/Facility-Provider/Adult-FamilyCare?type=1' },
];

const targetKeyFilter = String(process.env.AHCA_TARGET_KEY || '').trim();
const selectedTargets = targetKeyFilter
  ? targets.filter((target) => target.key === targetKeyFilter)
  : targets;

if (targetKeyFilter && selectedTargets.length === 0) {
  throw new Error(`Unknown AHCA_TARGET_KEY: ${targetKeyFilter}`);
}

const browser = await chromium.launch({
  headless: false,
  channel: 'chrome',
  args: ['--disable-blink-features=AutomationControlled'],
});
const context = await browser.newContext({
  acceptDownloads: true,
  locale: 'en-US',
  extraHTTPHeaders: {
    'accept-language': 'en-US,en;q=0.9',
    referer: 'https://quality.healthfinder.fl.gov/',
  },
});
const manifest = { started_at: new Date().toISOString(), targets: [] };

async function extractTables(page) {
  return page.evaluate(() => [...document.querySelectorAll('table')].map((table, tableIndex) => {
    const headers = [...table.querySelectorAll('thead th')].map(x => x.innerText.trim());
    const rows = [...table.querySelectorAll('tbody tr')].map(tr => [...tr.querySelectorAll('th,td')].map(td => td.innerText.trim()));
    return { tableIndex, headers, rows };
  }).filter(t => t.rows.length));
}

async function nextPage(page) {
  const selectors = [
    'a[aria-label="Next"]',
    'button[aria-label="Next"]',
    'a:has-text("Next")',
    'button:has-text("Next")',
    '.pagination .next:not(.disabled) a',
    'li.next:not(.disabled) a'
  ];
  for (const sel of selectors) {
    const loc = page.locator(sel).first();
    if (await loc.count()) {
      const disabled = await loc.getAttribute('disabled');
      const ariaDisabled = await loc.getAttribute('aria-disabled');
      if (disabled !== null || ariaDisabled === 'true') continue;
      await loc.click({ timeout: 5000 });
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(800);
      return true;
    }
  }
  return false;
}

for (const target of selectedTargets) {
  const page = await context.newPage();
  const record = { ...target, started_at: new Date().toISOString(), pages: 0, tables: 0, rows: 0, status: 'STARTED', errors: [] };
  manifest.targets.push(record);
  try {
    const response = await page.goto(target.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    record.http_status = response?.status() ?? null;
    record.final_url = page.url();
    record.title = await page.title();
    record.http_headers = response ? await response.allHeaders() : null;
    if (record.http_status === 403) throw new Error('HTTP 403/challenge in browser session');

    const all = [];
    const seenFingerprints = new Set();
    for (let i = 0; i < 500; i++) {
      await page.waitForTimeout(500);
      const tables = await extractTables(page);
      const fingerprint = JSON.stringify(tables.map(t => t.rows.slice(0, 2)));
      if (seenFingerprints.has(fingerprint)) break;
      seenFingerprints.add(fingerprint);
      all.push({ page_number: i + 1, url: page.url(), tables });
      record.pages++;
      record.tables += tables.length;
      record.rows += tables.reduce((n, t) => n + t.rows.length, 0);
      if (!(await nextPage(page))) break;
    }

    await fs.writeFile(path.join(OUT, `${target.key}.json`), JSON.stringify({ source: target, retrieved_at: new Date().toISOString(), pages: all }, null, 2));
    record.status = record.rows > 0 ? 'EXTRACTED' : 'NO_ROWS';
  } catch (e) {
    record.status = 'FAILED';
    record.errors.push(String(e?.stack || e));
    const pngPath = path.join(OUT, `${target.key}_failure.png`);
    await page.screenshot({ path: pngPath, fullPage: true }).catch(() => {});
    record.failure_screenshot = pngPath.replaceAll('\\', '/');
    await fs.writeFile(path.join(OUT, `${target.key}_failure.html`), await page.content().catch(() => ''), 'utf8');
  } finally {
    record.finished_at = new Date().toISOString();
    await page.close();
  }
}

manifest.finished_at = new Date().toISOString();
await fs.writeFile(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
await browser.close();
console.log(JSON.stringify(manifest, null, 2));
