const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');
const pythonExe = path.join(repoRoot, '.venv', 'Scripts', 'python.exe');

function runCommand(command, args, cwd) {
  const isWindowsNpm = process.platform === 'win32' && command === 'npm';
  const result = isWindowsNpm
    ? spawnSync('cmd.exe', ['/d', '/s', '/c', ['npm', ...args].join(' ')], {
      cwd,
      encoding: 'utf8',
      maxBuffer: 20 * 1024 * 1024,
    })
    : spawnSync(command, args, {
      cwd,
      encoding: 'utf8',
      maxBuffer: 20 * 1024 * 1024,
    });

  return {
    command: `${command} ${args.join(' ')}`,
    cwd,
    exitCode: result.status,
    output: `${result.stdout || ''}${result.stderr || ''}`.trim(),
    passed: result.status === 0,
  };
}

function parsePass(output, regex) {
  const match = output.match(regex);
  return match ? String(match[1]).toUpperCase() === 'PASS' : false;
}

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
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

function collectVisualCoverage() {
  const query = [
    'import json, sqlite3, pathlib',
    `db = pathlib.Path(r"${path.join(repoRoot, 'optime_nursing.db')}")`,
    'conn = sqlite3.connect(str(db))',
    'conn.row_factory = sqlite3.Row',
    'cur = conn.cursor()',
    'rows = cur.execute("""',
    'select',
    '  f.id as facility_id,',
    '  f.name as facility_name,',
    '  p.visual_confidence_score as visual_confidence_score,',
    '  p.visual_coverage_score as visual_coverage_score,',
    '  p.visual_hero_image as visual_hero_image,',
    '  p.visual_gallery_images as visual_gallery_images',
    'from facilities f',
    'left join facility_intelligence_profiles p on p.facility_id = f.id',
    'where f.state = ?',
    'order by f.id asc',
    '""", ("FL",)).fetchall()',
    'payload = []',
    'for row in rows:',
    '  hero = {}',
    '  gallery = []',
    '  try:',
    '    hero = json.loads(row["visual_hero_image"]) if row["visual_hero_image"] else {}',
    '  except Exception:',
    '    hero = {}',
    '  try:',
    '    gallery = json.loads(row["visual_gallery_images"]) if row["visual_gallery_images"] else []',
    '  except Exception:',
    '    gallery = []',
    '  payload.append({',
    '    "facility_id": row["facility_id"],',
    '    "facility_name": row["facility_name"],',
    '    "visual_confidence_score": float(row["visual_confidence_score"] or 0),',
    '    "visual_coverage_score": float(row["visual_coverage_score"] or 0),',
    '    "hero_source": hero.get("source", ""),',
    '    "gallery_count": len(gallery),',
    '  })',
    'print(json.dumps(payload))',
  ].join('\n');

  const result = spawnSync(pythonExe, ['-c', query], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (result.status !== 0) {
    return { passed: false, rows: [], averageCoverage: 0, detail: result.stderr || result.stdout || 'Python query failed.' };
  }

  const rows = JSON.parse(result.stdout || '[]');
  const averageCoverage = rows.length > 0
    ? Math.round((rows.reduce((sum, row) => sum + Number(row.visual_coverage_score || 0), 0) / rows.length) * 10) / 10
    : 0;
  const coveredCount = rows.filter((row) => Number(row.visual_coverage_score || 0) >= 70).length;
  const coverageRatio = rows.length > 0 ? Math.round((coveredCount / rows.length) * 1000) / 10 : 0;

  return {
    passed: averageCoverage >= 70,
    rows,
    averageCoverage,
    coverageRatio,
    detail: `Average visual coverage ${averageCoverage}% with ${coverageRatio}% facilities at >=70%.`,
  };
}

function main() {
  // Ensure intelligence profiles exist and simulation stays healthy.
  const simulation = runCommand('node', ['scripts/run_dynamic_persona_simulation_audit.cjs'], repoRoot);
  const simulationPass = simulation.passed && parsePass(simulation.output, /Verdict:\s+\*\*(PASS|FAIL)\*\*/i);

  const build = runCommand('npm', ['run', 'build'], path.join(repoRoot, 'frontend'));
  const benchmark = runCommand('node', ['scripts/run_human_advisor_benchmark.cjs'], repoRoot);
  const benchmarkPass = benchmark.passed && parsePass(benchmark.output, /Benchmark status:\s*(PASS|FAIL)/i);

  const coverage = collectVisualCoverage();
  const noRegressionPass = benchmarkPass;
  const overallPass = build.passed && simulationPass && coverage.passed && noRegressionPass;

  const reportLines = [];
  reportLines.push('# Visual Intelligence Validation Report');
  reportLines.push('');
  reportLines.push(`Overall Status: **${overallPass ? 'PASS' : 'FAIL'}**`);
  reportLines.push('');
  reportLines.push('## Validation Summary');
  reportLines.push('');
  reportLines.push(`- Build PASS: **${build.passed ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`- Simulation PASS: **${simulationPass ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`- At least 70% image coverage: **${coverage.passed ? 'PASS' : 'FAIL'}** (${coverage.averageCoverage}%)`);
  reportLines.push(`- No ranking regressions: **${noRegressionPass ? 'PASS' : 'FAIL'}**`);
  reportLines.push('');
  reportLines.push('## Coverage Metrics');
  reportLines.push('');
  reportLines.push(`- ${coverage.detail}`);
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Facility ID', 'Community', 'Hero Source', 'Gallery Count', 'Visual Coverage %', 'Visual Confidence'],
    (coverage.rows || []).slice(0, 200).map((row) => [
      row.facility_id,
      row.facility_name,
      row.hero_source || 'N/A',
      row.gallery_count,
      row.visual_coverage_score,
      row.visual_confidence_score,
    ]),
  ));

  const markdownPath = path.join(repoRoot, 'reports', 'visual_intelligence_validation_report.md');
  fs.writeFileSync(markdownPath, reportLines.join('\n'));

  const csvHeaders = ['facility_id', 'community', 'hero_source', 'gallery_count', 'visual_coverage_score', 'visual_confidence_score'];
  const csvRows = [csvHeaders.join(',')];
  (coverage.rows || []).forEach((row) => {
    csvRows.push([
      csvEscape(row.facility_id),
      csvEscape(row.facility_name),
      csvEscape(row.hero_source || 'N/A'),
      csvEscape(row.gallery_count),
      csvEscape(row.visual_coverage_score),
      csvEscape(row.visual_confidence_score),
    ].join(','));
  });
  const csvPath = path.join(repoRoot, 'reports', 'visual_intelligence_validation_report.csv');
  fs.writeFileSync(csvPath, csvRows.join('\n'));

  console.log(`Wrote ${markdownPath}`);
  console.log(`Wrote ${csvPath}`);
  console.log(`Build PASS=${build.passed ? 'PASS' : 'FAIL'}`);
  console.log(`Simulation PASS=${simulationPass ? 'PASS' : 'FAIL'}`);
  console.log(`IMAGE_COVERAGE_PASS=${coverage.passed ? 'PASS' : 'FAIL'} AVG=${coverage.averageCoverage}%`);
  console.log(`RANKING_REGRESSION_PASS=${noRegressionPass ? 'PASS' : 'FAIL'}`);

  if (!overallPass) {
    process.exitCode = 1;
  }
}

main();
