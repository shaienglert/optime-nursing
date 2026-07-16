const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function runPython(code) {
  const pythonPath = path.join(repoRoot, '.venv', 'Scripts', 'python.exe');
  const result = spawnSync(pythonPath, ['-c', code], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 40 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error((result.stderr || result.stdout || 'Python execution failed').trim());
  }

  return result.stdout;
}

function provenanceOf(source, category, signalName) {
  const src = String(source || '').toLowerCase();
  const categoryNorm = String(category || '').toLowerCase();
  const signalNorm = String(signalName || '').toLowerCase();

  if (['cms', 'medicare care compare', 'state inspections', 'ahca', 'public court records'].includes(src)) {
    return 'REAL';
  }

  if (['google reviews', 'indeed', 'glassdoor', 'facebook', 'instagram', 'linkedin', 'yelp'].includes(src)) {
    return 'SYNTHETIC';
  }

  if (categoryNorm === 'social_signals' || categoryNorm === 'news' || src === 'official websites' || src === 'public event calendars' || src === 'press releases' || src === 'local news') {
    return 'HEURISTIC';
  }

  if (categoryNorm === 'family_sentiment' || categoryNorm === 'employee_intelligence' || signalNorm.includes('satisfaction') || signalNorm.includes('stability')) {
    return 'INFERRED';
  }

  return 'INFERRED';
}

function methodOf(source, category, signalName) {
  const src = String(source || '').toLowerCase();
  const categoryNorm = String(category || '').toLowerCase();
  const signalNorm = String(signalName || '').toLowerCase();

  if (src === 'cms' || src === 'medicare care compare' || src === 'state inspections' || src === 'ahca') {
    return 'regulatory_ingest';
  }
  if (src === 'public court records') {
    return 'legal_risk_derived';
  }
  if (['google reviews', 'indeed', 'glassdoor', 'facebook', 'instagram', 'linkedin', 'yelp'].includes(src)) {
    return 'wave3_activation_fallback';
  }
  if (categoryNorm === 'social_signals') {
    return 'social_heuristic_parser';
  }
  if (categoryNorm === 'news') {
    return 'news_heuristic_parser';
  }
  if (categoryNorm === 'family_sentiment' || categoryNorm === 'employee_intelligence' || signalNorm.includes('satisfaction')) {
    return 'review_aggregate_inference';
  }
  return 'intelligence_inference';
}

function rawUrlOf(source) {
  const src = String(source || '').toLowerCase();
  const map = {
    'cms': 'https://data.cms.gov/',
    'medicare care compare': 'https://www.medicare.gov/care-compare/',
    'state inspections': 'https://ahca.myflorida.com/',
    'ahca': 'https://ahca.myflorida.com/',
    'public court records': 'https://www.courtlistener.com/',
    'google reviews': 'https://www.google.com/maps',
    'indeed': 'https://www.indeed.com/',
    'glassdoor': 'https://www.glassdoor.com/',
    'facebook': 'https://www.facebook.com/',
    'instagram': 'https://www.instagram.com/',
    'linkedin': 'https://www.linkedin.com/',
    'yelp': 'https://www.yelp.com/',
    'local news': 'https://news.google.com/',
    'press releases': 'https://www.prnewswire.com/',
    'official websites': 'N/A',
    'public event calendars': 'N/A',
  };
  return map[src] || 'N/A';
}

function collectSignals() {
  const backendPath = path.join(repoRoot, 'backend').replace(/\\/g, '\\\\');
  const pythonCode = [
    'import json, sys',
    `sys.path.insert(0, r"${backendPath}")`,
    'from app.database import SessionLocal',
    'from app.models.facility import Facility',
    'import app.services.intelligence_agent as ia',
    '',
    'db = SessionLocal()',
    'rows = []',
    'facilities = db.query(Facility).order_by(Facility.id.asc()).all()',
    'for facility in facilities:',
    '    signals = []',
    '    signals.extend(ia._collect_regulatory_signals(db, facility))',
    '    signals.extend(ia._collect_review_signals(db, facility))',
    '    signals.extend(ia._collect_social_signals(facility))',
    '    signals.extend(ia._collect_news_signals(facility))',
    '    signals.extend(ia._collect_legal_signals(facility))',
    '    if hasattr(ia, "_collect_activation_wave3_signals"):',
    '        signals.extend(ia._collect_activation_wave3_signals(facility))',
    '    deduped = ia._deduplicate_signals(signals)',
    '    for signal in deduped:',
    '        rows.append({',
    '            "facility_name": facility.name,',
    '            "source": signal.get("source", ""),',
    '            "category": signal.get("category", ""),',
    '            "signal_name": signal.get("signal", ""),',
    '            "collection_timestamp": signal.get("date", ""),',
    '            "raw_text_snippet": signal.get("summary", ""),',
    '            "confidence": signal.get("confidence", 0),',
    '        })',
    'db.close()',
    'print(json.dumps(rows))',
  ].join('\n');

  return JSON.parse(runPython(pythonCode));
}

function main() {
  const signals = collectSignals();

  const enriched = signals.map((signal) => {
    const source = signal.source || '';
    const category = signal.category || '';
    const signalName = signal.signal_name || '';

    const provenance = provenanceOf(source, category, signalName);
    return {
      facility_name: signal.facility_name,
      source,
      collection_method: methodOf(source, category, signalName),
      collection_timestamp: signal.collection_timestamp || new Date().toISOString().slice(0, 10),
      raw_url: rawUrlOf(source),
      raw_text_snippet: signal.raw_text_snippet || '',
      confidence: Number(signal.confidence || 0).toFixed(1),
      synthetic_or_real: provenance,
    };
  });

  const total = enriched.length || 1;
  const counts = {
    REAL: enriched.filter((row) => row.synthetic_or_real === 'REAL').length,
    SYNTHETIC: enriched.filter((row) => row.synthetic_or_real === 'SYNTHETIC').length,
    HEURISTIC: enriched.filter((row) => row.synthetic_or_real === 'HEURISTIC').length,
    INFERRED: enriched.filter((row) => row.synthetic_or_real === 'INFERRED').length,
  };

  const pct = {
    REAL: ((counts.REAL / total) * 100).toFixed(1),
    SYNTHETIC: ((counts.SYNTHETIC / total) * 100).toFixed(1),
    HEURISTIC: ((counts.HEURISTIC / total) * 100).toFixed(1),
    INFERRED: ((counts.INFERRED / total) * 100).toFixed(1),
  };

  const lines = [];
  lines.push('# OSINT Provenance Audit');
  lines.push('');
  lines.push(`Generated At: ${new Date().toISOString()}`);
  lines.push(`Total Signals Audited: ${enriched.length}`);
  lines.push('');
  lines.push('## Summary');
  lines.push('');
  lines.push(`- REAL signals count: ${counts.REAL}`);
  lines.push(`- SYNTHETIC signals count: ${counts.SYNTHETIC}`);
  lines.push(`- HEURISTIC signals count: ${counts.HEURISTIC}`);
  lines.push(`- INFERRED signals count: ${counts.INFERRED}`);
  lines.push('');
  lines.push('### Coverage Percentages By Provenance Type');
  lines.push('');
  lines.push(markdownTable(
    ['Provenance Type', 'Count', 'Coverage %'],
    [
      ['REAL', counts.REAL, `${pct.REAL}%`],
      ['SYNTHETIC', counts.SYNTHETIC, `${pct.SYNTHETIC}%`],
      ['HEURISTIC', counts.HEURISTIC, `${pct.HEURISTIC}%`],
      ['INFERRED', counts.INFERRED, `${pct.INFERRED}%`],
    ]
  ));
  lines.push('');
  lines.push('## Signals');
  lines.push('');
  lines.push(markdownTable(
    ['facility_name', 'source', 'collection_method', 'collection_timestamp', 'raw_url', 'raw_text_snippet', 'confidence', 'synthetic_or_real'],
    enriched.map((row) => [
      row.facility_name,
      row.source,
      row.collection_method,
      row.collection_timestamp,
      row.raw_url,
      row.raw_text_snippet,
      row.confidence,
      row.synthetic_or_real,
    ])
  ));

  const outPath = path.join(repoRoot, 'reports', 'osint_provenance_audit.md');
  fs.writeFileSync(outPath, lines.join('\n'));

  console.log(`Wrote ${outPath}`);
  console.log(`REAL signals count: ${counts.REAL}`);
  console.log(`SYNTHETIC signals count: ${counts.SYNTHETIC}`);
  console.log(`HEURISTIC signals count: ${counts.HEURISTIC}`);
  console.log(`INFERRED signals count: ${counts.INFERRED}`);
  console.log(`Coverage % REAL=${pct.REAL}, SYNTHETIC=${pct.SYNTHETIC}, HEURISTIC=${pct.HEURISTIC}, INFERRED=${pct.INFERRED}`);
}

main();
