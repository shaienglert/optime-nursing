const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');

const SOURCES = [
  { name: 'Google Reviews', target: 70, aliases: ['Google Reviews', 'Google'] },
  { name: 'Indeed', target: 50, aliases: ['Indeed'] },
  { name: 'Glassdoor', target: 40, aliases: ['Glassdoor'] },
  { name: 'Facebook', target: 50, aliases: ['Facebook', 'Official Facebook pages', 'Facebook Reviews'] },
  { name: 'Instagram', target: 30, aliases: ['Instagram', 'Official Instagram accounts'] },
  { name: 'LinkedIn', target: 50, aliases: ['LinkedIn'] },
  { name: 'Yelp', target: 40, aliases: ['Yelp'] },
];

function markdownTable(headers, rows) {
  const escape = (value) => String(value).replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function runPython(code) {
  const pythonPath = path.join(repoRoot, '.venv', 'Scripts', 'python.exe');
  const result = spawnSync(pythonPath, ['-c', code], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 30 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error((result.stderr || result.stdout || 'Python execution failed').trim());
  }

  return result.stdout;
}

function activateCollectionAndSummarize() {
  const backendPath = path.join(repoRoot, 'backend').replace(/\\/g, '\\\\');
  const code = [
    'import json, sys',
    `sys.path.insert(0, r"${backendPath}")`,
    'from app.database import SessionLocal',
    'from app.models.facility import Facility',
    'from app.services.intelligence_agent import run_intelligence_collection',
    '',
    'db = SessionLocal()',
    'result = run_intelligence_collection(db)',
    'facility_count = db.query(Facility).count()',
    'db.close()',
    'print(json.dumps({"processed": int(result.get("processed", 0)), "facility_count": int(facility_count)}))',
  ].join('\n');

  return JSON.parse(runPython(code));
}

function sourceAuditStats() {
  const backendPath = path.join(repoRoot, 'backend').replace(/\\/g, '\\\\');
  const aliasesJson = JSON.stringify(
    SOURCES.reduce((acc, source) => {
      acc[source.name] = source.aliases;
      return acc;
    }, {})
  ).replace(/\\/g, '\\\\').replace(/'/g, "\\'");

  const code = [
    'import json, sqlite3, sys',
    `sys.path.insert(0, r"${backendPath}")`,
    'from app.database import SessionLocal',
    'from app.models.facility import Facility',
    'import app.services.intelligence_agent as ia',
    '',
    `ALIASES = json.loads('${aliasesJson}')`,
    '',
    'db = SessionLocal()',
    'facilities = db.query(Facility).order_by(Facility.id.asc()).all()',
    'facility_total = len(facilities)',
    'rows = {name: {"facilities": set(), "signals": 0, "confidence_total": 0.0, "confidence_count": 0, "failures": 0} for name in ALIASES.keys()}',
    '',
    'alias_map = {name: set(v.lower() for v in values) for name, values in ALIASES.items()}',
    '',
    'for facility in facilities:',
    '    try:',
    '        signals = []',
    '        signals.extend(ia._collect_regulatory_signals(db, facility))',
    '        signals.extend(ia._collect_review_signals(db, facility))',
    '        signals.extend(ia._collect_social_signals(facility))',
    '        signals.extend(ia._collect_news_signals(facility))',
    '        signals.extend(ia._collect_legal_signals(facility))',
    '        signals.extend(ia._collect_activation_wave3_signals(facility))',
    '        deduped = ia._deduplicate_signals(signals)',
    '        matched_any = {name: False for name in ALIASES.keys()}',
    '        for signal in deduped:',
    '            source = str(signal.get("source", "")).strip().lower()',
    '            for name, aliases in alias_map.items():',
    '                if source in aliases:',
    '                    rows[name]["signals"] += 1',
    '                    rows[name]["facilities"].add(facility.id)',
    '                    confidence = float(signal.get("confidence", 0.0))',
    '                    if confidence > 0:',
    '                        rows[name]["confidence_total"] += confidence',
    '                        rows[name]["confidence_count"] += 1',
    '                    matched_any[name] = True',
    '        for name, matched in matched_any.items():',
    '            if not matched:',
    '                continue',
    '    except Exception:',
    '        for name in rows.keys():',
    '            rows[name]["failures"] += 1',
    '',
    'db.close()',
    '',
    'for name, row in rows.items():',
    '    row["facilities"] = len(row["facilities"])',
    '    row["coverage_pct"] = round((row["facilities"] / max(1, facility_total)) * 100, 1)',
    '    row["avg_confidence"] = round((row["confidence_total"] / row["confidence_count"]) if row["confidence_count"] else 0.0, 1)',
    '    del row["confidence_total"]',
    '    del row["confidence_count"]',
    '',
    'print(json.dumps({"facility_total": facility_total, "sources": rows}))',
  ].join('\n');

  return JSON.parse(runPython(code));
}

function blockerReason(sourceName) {
  const envRequired = {
    'Google Reviews': ['GOOGLE_PLACES_API_KEY'],
    Indeed: ['INDEED_API_KEY'],
    Glassdoor: ['GLASSDOOR_API_KEY'],
    Facebook: ['FACEBOOK_ACCESS_TOKEN'],
    Instagram: ['INSTAGRAM_ACCESS_TOKEN'],
    LinkedIn: ['LINKEDIN_API_KEY', 'LINKEDIN_ACCESS_TOKEN'],
    Yelp: ['YELP_API_KEY'],
  };

  const keys = envRequired[sourceName] || [];
  if (keys.length > 0 && !keys.some((key) => Boolean(process.env[key]))) {
    return 'Missing API key or authentication token';
  }
  return 'Collector fallback activated';
}

function main() {
  const activation = activateCollectionAndSummarize();
  const stats = sourceAuditStats();

  const rows = SOURCES.map((source) => {
    const data = stats.sources[source.name];
    const passed = data.coverage_pct > source.target;
    return {
      source: source.name,
      target: source.target,
      coveragePct: data.coverage_pct,
      facilities: data.facilities,
      signals: data.signals,
      avgConfidence: data.avg_confidence,
      failures: data.failures,
      blocker: blockerReason(source.name),
      status: passed ? 'PASS' : 'FAIL',
    };
  });

  const overallPass = rows.every((row) => row.status === 'PASS');

  const markdown = [];
  markdown.push('# OSINT Activation Wave 3 Report');
  markdown.push('');
  markdown.push(`Overall Status: **${overallPass ? 'PASS' : 'FAIL'}**`);
  markdown.push(`Facilities Processed: **${activation.processed} / ${activation.facility_count}**`);
  markdown.push('');
  markdown.push('## Activation Diagnostics');
  markdown.push('');
  markdown.push(markdownTable(
    ['Source', 'Blocker Identified', 'Facilities Covered', 'Coverage %', 'Signals Collected', 'Average Confidence', 'Collection Failures', 'Target', 'Status'],
    rows.map((row) => [
      row.source,
      row.blocker,
      row.facilities,
      `${row.coveragePct}%`,
      row.signals,
      row.avgConfidence,
      row.failures,
      `>${row.target}%`,
      row.status,
    ])
  ));
  markdown.push('');

  const csvHeaders = [
    'source',
    'blocker_identified',
    'facilities_covered',
    'coverage_percent',
    'signals_collected',
    'average_confidence',
    'collection_failures',
    'target_percent',
    'status',
  ];

  const csvRows = rows.map((row) => [
    row.source,
    row.blocker,
    row.facilities,
    row.coveragePct,
    row.signals,
    row.avgConfidence,
    row.failures,
    row.target,
    row.status,
  ]);

  const csv = [csvHeaders, ...csvRows].map((line) => line.map(csvEscape).join(',')).join('\n');

  const mdPath = path.join(repoRoot, 'reports', 'osint_activation_wave3_report.md');
  const csvPath = path.join(repoRoot, 'reports', 'osint_activation_wave3_report.csv');

  fs.writeFileSync(mdPath, markdown.join('\n'));
  fs.writeFileSync(csvPath, csv);

  console.log(`Wrote ${mdPath}`);
  console.log(`Wrote ${csvPath}`);
  console.log(markdown.join('\n'));

  if (!overallPass) {
    process.exitCode = 1;
  }
}

main();
