const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');

function markdownTable(headers, rows) {
  const escape = (value) => String(value).replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function runAudit() {
  const pythonPath = path.join(repoRoot, '.venv', 'Scripts', 'python.exe');
  const dbPath = path.join(repoRoot, 'optime_nursing.db').replace(/\\/g, '\\\\');
  const backendPath = path.join(repoRoot, 'backend').replace(/\\/g, '\\\\');

  const pythonCode = [
    'import json',
    'import os',
    'import sqlite3',
    'import sys',
    `sys.path.insert(0, r"${backendPath}")`,
    'from app.database import SessionLocal',
    'from app.models.facility import Facility',
    'import app.services.intelligence_agent as ia',
    '',
    'SOURCE_ALIASES = {',
    '    "Court records": ["Public court records", "Lawsuits", "Settlements", "Regulatory actions", "Enforcement actions", "State court records", "Federal court records"],',
    '    "Google Reviews": ["Google Reviews", "Google"],',
    '    "Indeed": ["Indeed"],',
    '    "Glassdoor": ["Glassdoor"],',
    '    "Facebook": ["Facebook", "Official Facebook pages", "Facebook Reviews"],',
    '    "Instagram": ["Instagram", "Official Instagram accounts"],',
    '    "Reddit": ["Reddit"],',
    '    "BBB": ["BBB", "Better Business Bureau"],',
    '    "Yelp": ["Yelp"],',
    '    "LinkedIn": ["LinkedIn"],',
    '    "Local news": ["Local news", "Press releases", "TV stations"],',
    '    "CMS": ["CMS"],',
    '    "Medicare": ["Medicare Care Compare", "Medicare"],',
    '    "State inspections": ["State inspections", "AHCA", "Deficiency reports", "Staffing reports"],',
    '}',
    '',
    'COLLECTOR_MAP = {',
    '    "Court records": True,',
    '    "Google Reviews": True,',
    '    "Indeed": True,',
    '    "Glassdoor": True,',
    '    "Facebook": True,',
    '    "Instagram": True,',
    '    "Reddit": False,',
    '    "BBB": False,',
    '    "Yelp": True,',
    '    "LinkedIn": True,',
    '    "Local news": True,',
    '    "CMS": True,',
    '    "Medicare": True,',
    '    "State inspections": True,',
    '}',
    '',
    'def aliases_for(source_name):',
    '    return set(s.lower() for s in SOURCE_ALIASES.get(source_name, []))',
    '',
    'db = SessionLocal()',
    'facilities = db.query(Facility).order_by(Facility.id.asc()).all()',
    '',
    'source_facilities = {name: set() for name in SOURCE_ALIASES.keys()}',
    'source_signals = {name: 0 for name in SOURCE_ALIASES.keys()}',
    '',
    'for facility in facilities:',
    '    all_signals = []',
    '    all_signals.extend(ia._collect_regulatory_signals(db, facility))',
    '    all_signals.extend(ia._collect_review_signals(db, facility))',
    '    all_signals.extend(ia._collect_social_signals(facility))',
    '    all_signals.extend(ia._collect_news_signals(facility))',
    '    all_signals.extend(ia._collect_legal_signals(facility))',
    '    if hasattr(ia, "_collect_activation_wave3_signals"):',
    '        all_signals.extend(ia._collect_activation_wave3_signals(facility))',
    '    deduped = ia._deduplicate_signals(all_signals)',
    '    for signal in deduped:',
    '        source = str(signal.get("source", "")).strip().lower()',
    '        for canonical in SOURCE_ALIASES.keys():',
    '            if source in aliases_for(canonical):',
    '                source_facilities[canonical].add(facility.id)',
    '                source_signals[canonical] += 1',
    '',
    'db.close()',
    '',
    'conn = sqlite3.connect(r"' + dbPath + '")',
    'conn.row_factory = sqlite3.Row',
    'rows = conn.execute("select facility_id, last_updated, sources_used from facility_intelligence_profiles").fetchall()',
    'conn.close()',
    '',
    'last_success = {name: None for name in SOURCE_ALIASES.keys()}',
    'for row in rows:',
    '    last_updated = row["last_updated"]',
    '    try:',
    '        sources = json.loads(row["sources_used"] or "[]")',
    '    except Exception:',
    '        sources = []',
    '    normalized = set(str(s).strip().lower() for s in sources)',
    '    for canonical in SOURCE_ALIASES.keys():',
    '        if normalized.intersection(aliases_for(canonical)):',
    '            prev = last_success[canonical]',
    '            if prev is None or (last_updated and str(last_updated) > str(prev)):',
    '                last_success[canonical] = last_updated',
    '',
    'registry = ia.PUBLIC_SOURCE_REGISTRY',
    'configured = {}',
    'for canonical in SOURCE_ALIASES.keys():',
    '    alias = aliases_for(canonical)',
    '    is_configured = False',
    '    for items in registry.values():',
    '        norm_items = set(str(v).strip().lower() for v in items)',
    '        if norm_items.intersection(alias):',
    '            is_configured = True',
    '            break',
    '    configured[canonical] = is_configured',
    '',
    'out = {}',
    'for canonical in SOURCE_ALIASES.keys():',
    '    out[canonical] = {',
    '        "configured": configured[canonical],',
    '        "collector_implemented": bool(COLLECTOR_MAP.get(canonical, False)),',
    '        "facilities_with_data": len(source_facilities[canonical]),',
    '        "signals_collected": int(source_signals[canonical]),',
    '        "last_successful_collection_date": last_success[canonical],',
    '    }',
    '',
    'print(json.dumps(out))',
  ].join('\n');

  const result = spawnSync(pythonPath, ['-c', pythonCode], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error(`Coverage audit failed: ${result.stderr || result.stdout}`.trim());
  }

  return JSON.parse(result.stdout);
}

function credentialsAvailable(source) {
  const envMap = {
    'Court records': ['COURT_RECORDS_API_KEY', 'COURTLISTENER_API_KEY'],
    'Google Reviews': ['GOOGLE_PLACES_API_KEY'],
    Indeed: ['INDEED_API_KEY'],
    Glassdoor: ['GLASSDOOR_API_KEY'],
    Facebook: ['FACEBOOK_ACCESS_TOKEN'],
    Instagram: ['INSTAGRAM_ACCESS_TOKEN'],
    Reddit: ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET'],
    BBB: ['BBB_API_KEY'],
    Yelp: ['YELP_API_KEY'],
    LinkedIn: ['LINKEDIN_API_KEY', 'LINKEDIN_ACCESS_TOKEN'],
    'Local news': [],
    CMS: [],
    Medicare: [],
    'State inspections': [],
  };

  const keys = envMap[source] || [];
  if (keys.length === 0) {
    return true;
  }
  return keys.some((key) => Boolean(process.env[key]));
}

function buildReport(auditRows) {
  const rows = Object.entries(auditRows).map(([source, row]) => {
    const configured = row.configured ? 'YES' : 'NO';
    const implemented = row.collector_implemented ? 'YES' : 'NO';
    const credentials = credentialsAvailable(source) ? 'YES' : 'NO';
    const facilitiesCovered = row.facilities_with_data;
    const signalsCollected = row.signals_collected;
    const active = configured === 'YES' && implemented === 'YES' && facilitiesCovered > 0 ? 'YES' : 'NO';
    const lastDate = row.last_successful_collection_date || 'N/A';

    return {
      source,
      configured,
      implemented,
      credentials,
      lastDate,
      facilitiesCovered,
      signalsCollected,
      active,
    };
  });

  rows.sort((a, b) => a.source.localeCompare(b.source));

  const md = [];
  md.push('# OSINT Source Coverage Audit');
  md.push('');
  md.push(`Generated At: ${new Date().toISOString()}`);
  md.push('');
  md.push('## Detailed Audit');
  md.push('');
  md.push(markdownTable(
    ['Source', 'Configured', 'Collector Implemented', 'Credentials/API Available', 'Last Successful Collection Date', 'Facilities With Data', 'Signals Collected'],
    rows.map((row) => [
      row.source,
      row.configured,
      row.implemented,
      row.credentials,
      row.lastDate,
      row.facilitiesCovered,
      row.signalsCollected,
    ])
  ));
  md.push('');
  md.push('## Final Output');
  md.push('');
  md.push(markdownTable(
    ['Source', 'Implemented', 'Active', 'Facilities Covered', 'Signals Collected'],
    rows.map((row) => [row.source, row.implemented, row.active, row.facilitiesCovered, row.signalsCollected])
  ));
  md.push('');

  return md.join('\n');
}

function main() {
  const auditRows = runAudit();
  const report = buildReport(auditRows);
  const outPath = path.join(repoRoot, 'reports', 'osint_source_coverage_audit.md');
  fs.writeFileSync(outPath, report);
  console.log(`Wrote ${outPath}`);
  console.log(report);
}

main();
