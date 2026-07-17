const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const benchmarkHelpers = require('./run_human_advisor_benchmark.cjs');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');

const {
  buildPersonas,
  buildBenchmarkResults,
} = benchmarkHelpers;
const {
  loadBackendFacilities,
  toSearchFacility,
} = simulationHelpers;

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function carePhilosophyLabel(careTypes) {
  if (careTypes.includes('Memory Care')) return 'memory-support';
  if (careTypes.includes('Rehabilitation')) return 'rehabilitation-first';
  if (careTypes.includes('Skilled Nursing')) return 'clinical-first';
  if (careTypes.includes('CCRC') || careTypes.includes('Continuing Care')) return 'continuum-first';
  if (careTypes.includes('Independent Living') || careTypes.includes('Active Adult 55+')) return 'independence-first';
  if (careTypes.includes('Assisted Living')) return 'assisted-living-first';
  return 'mixed-support';
}

function futureSupportLabel(careTypes) {
  if (careTypes.includes('CCRC') || careTypes.includes('Continuing Care')) return 'full continuum';
  if ((careTypes.includes('Independent Living') || careTypes.includes('Active Adult 55+')) && careTypes.includes('Assisted Living')) return 'future support available';
  if (careTypes.includes('Independent Living') || careTypes.includes('Active Adult 55+')) return 'independent only';
  if (careTypes.includes('Skilled Nursing') || careTypes.includes('Rehabilitation')) return 'clinical support only';
  return 'limited future support visibility';
}

function independenceFirstLabel(careTypes) {
  if (careTypes.includes('Independent Living') || careTypes.includes('Active Adult 55+')) {
    if (careTypes.includes('Skilled Nursing') || careTypes.includes('Rehabilitation')) return 'mixed independence and clinical';
    return 'independence-first';
  }
  return 'not independence-first';
}

function geographicLabel(item) {
  const familyFit = item.priorityScores.familyFit;
  if (familyFit >= 75) return 'strong geographic fit';
  if (familyFit >= 55) return 'moderate geographic fit';
  return 'weak geographic fit';
}

function budgetLabel(item) {
  const financialFit = item.priorityScores.financialFit;
  if (financialFit >= 85) return 'strong budget fit';
  if (financialFit >= 65) return 'moderate budget fit';
  return 'weak budget fit';
}

function findAdvisorOnly(optimeTop5, advisorTop5) {
  const optimeIds = new Set(optimeTop5.map((item) => item.facility.id));
  return advisorTop5.filter((item) => !optimeIds.has(item.facility.id));
}

function pairDisagreements(result) {
  const advisorOnly = findAdvisorOnly(result.optimeTop5, result.advisorTop5);
  const advisorOnlyByRank = advisorOnly.slice();
  const advisorSet = new Set(result.advisorTop5.map((item) => item.facility.id));
  const optimeOnly = result.optimeTop5.filter((item) => !advisorSet.has(item.facility.id));

  return optimeOnly.map((optimeItem, index) => ({
    persona: result.persona,
    engineOutput: result.engineOutput,
    optimeItem,
    advisorItem: advisorOnlyByRank[index] || null,
  }));
}

function classifyDisagreement(pair) {
  const { persona, optimeItem, advisorItem } = pair;
  if (!advisorItem) {
    return {
      classification: 'missing dataset information',
      rationale: 'No clear advisor-only counterpart was available to pair with this OPTIME-only recommendation.',
    };
  }

  const optimeCare = carePhilosophyLabel(optimeItem.facility.careTypes);
  const advisorCare = carePhilosophyLabel(advisorItem.facility.careTypes);
  const optimeFuture = futureSupportLabel(optimeItem.facility.careTypes);
  const advisorFuture = futureSupportLabel(advisorItem.facility.careTypes);
  const optimeIndependence = independenceFirstLabel(optimeItem.facility.careTypes);
  const advisorIndependence = independenceFirstLabel(advisorItem.facility.careTypes);
  const optimeGeo = geographicLabel(optimeItem);
  const advisorGeo = geographicLabel(advisorItem);
  const optimeBudget = budgetLabel(optimeItem);
  const advisorBudget = budgetLabel(advisorItem);

  const excludedMismatch = optimeItem.facility.careTypes.some((type) => persona.advisor.excludedCareTypes.includes(type));
  const preferredGap = advisorItem.facility.careTypes.some((type) => persona.advisor.preferredCareTypes.includes(type)) && !optimeItem.facility.careTypes.some((type) => persona.advisor.preferredCareTypes.includes(type));
  const sameCarePhilosophy = optimeCare === advisorCare;
  const sameFutureSupport = optimeFuture === advisorFuture;
  const sameIndependence = optimeIndependence === advisorIndependence;
  const sameGeo = optimeGeo === advisorGeo;
  const sameBudget = optimeBudget === advisorBudget;
  const scoreGap = Math.abs(optimeItem.totalScore - advisorItem.totalScore);

  if (sameCarePhilosophy && sameFutureSupport && sameIndependence && sameGeo && sameBudget && scoreGap <= 5) {
    return {
      classification: 'acceptable disagreement',
      rationale: 'Both communities express materially similar support philosophy and constraint fit; this is a near-substitute ranking difference.',
    };
  }

  if (excludedMismatch || preferredGap) {
    return {
      classification: 'scoring issue',
      rationale: 'The advisor preference model clearly favors the advisor recommendation over the OPTIME selection, but the ranking still elevated the OPTIME result.',
    };
  }

  const optimeHasMixed = optimeItem.facility.careTypes.length !== new Set(optimeItem.facility.careTypes).size;
  const advisorHasMixed = advisorItem.facility.careTypes.length !== new Set(advisorItem.facility.careTypes).size;
  if (optimeHasMixed || advisorHasMixed) {
    return {
      classification: 'taxonomy issue',
      rationale: 'Care taxonomy shape likely influenced the disagreement more than person-fit evidence.',
    };
  }

  return {
    classification: 'missing dataset information',
    rationale: 'The disagreement likely depends on facility evidence not present in the current structured dataset.',
  };
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const personas = buildPersonas();
  const results = buildBenchmarkResults(facilities, personas);

  const pairs = results.flatMap((result) => pairDisagreements(result));
  const analyzed = pairs.map((pair) => {
    const outcome = classifyDisagreement(pair);
    const advisorItem = pair.advisorItem;
    return {
      ...pair,
      ...outcome,
      carePhilosophyDifference: `${carePhilosophyLabel(pair.optimeItem.facility.careTypes)} vs ${advisorItem ? carePhilosophyLabel(advisorItem.facility.careTypes) : 'none'}`,
      futureSupportDifference: `${futureSupportLabel(pair.optimeItem.facility.careTypes)} vs ${advisorItem ? futureSupportLabel(advisorItem.facility.careTypes) : 'none'}`,
      independenceFirstDifference: `${independenceFirstLabel(pair.optimeItem.facility.careTypes)} vs ${advisorItem ? independenceFirstLabel(advisorItem.facility.careTypes) : 'none'}`,
      geographicDifference: `${geographicLabel(pair.optimeItem)} vs ${advisorItem ? geographicLabel(advisorItem) : 'none'}`,
      budgetDifference: `${budgetLabel(pair.optimeItem)} vs ${advisorItem ? budgetLabel(advisorItem) : 'none'}`,
    };
  });

  const acceptableCount = analyzed.filter((item) => item.classification === 'acceptable disagreement').length;
  const trueDisagreements = analyzed.filter((item) => item.classification !== 'acceptable disagreement');
  const totalSlots = results.length * 5;
  const rawDisagreementRate = Number(((analyzed.length / totalSlots) * 100).toFixed(1));
  const trueDisagreementRate = Number(((trueDisagreements.length / totalSlots) * 100).toFixed(1));

  const lines = [];
  lines.push('# Benchmark Gap Analysis V1');
  lines.push('');
  lines.push('## Summary');
  lines.push('');
  lines.push(`- Personas analyzed: **${results.length}**`);
  lines.push(`- Total benchmark slots: **${totalSlots}**`);
  lines.push(`- Raw disagreements: **${analyzed.length}**`);
  lines.push(`- Acceptable disagreements: **${acceptableCount}**`);
  lines.push(`- True disagreements: **${trueDisagreements.length}**`);
  lines.push(`- Raw disagreement rate: **${rawDisagreementRate}%**`);
  lines.push(`- True disagreement rate excluding acceptable disagreements: **${trueDisagreementRate}%**`);
  lines.push('');
  lines.push('## Classification Summary');
  lines.push('');
  const classificationRows = ['acceptable disagreement', 'scoring issue', 'taxonomy issue', 'missing dataset information'].map((classification) => [
    classification,
    analyzed.filter((item) => item.classification === classification).length,
  ]);
  lines.push(markdownTable(['Classification', 'Count'], classificationRows));
  lines.push('');

  analyzed.forEach((item, index) => {
    lines.push(`## Disagreement ${index + 1}: ${item.persona.name}`);
    lines.push('');
    lines.push(`- Classification: **${item.classification}**`);
    lines.push(`- OPTIME recommendation: **${item.optimeItem.facility.name}** (${item.optimeItem.facility.careTypes.join(', ')})`);
    lines.push(`- Advisor recommendation: **${item.advisorItem ? item.advisorItem.facility.name : 'None'}**${item.advisorItem ? ` (${item.advisorItem.facility.careTypes.join(', ')})` : ''}`);
    lines.push(`- Care philosophy difference: ${item.carePhilosophyDifference}`);
    lines.push(`- Future support difference: ${item.futureSupportDifference}`);
    lines.push(`- Independence-first difference: ${item.independenceFirstDifference}`);
    lines.push(`- Geographic difference: ${item.geographicDifference}`);
    lines.push(`- Budget difference: ${item.budgetDifference}`);
    lines.push(`- Rationale: ${item.rationale}`);
    lines.push('');
  });

  const reportPath = path.join(repoRoot, 'reports', 'benchmark_gap_analysis.md');
  fs.writeFileSync(reportPath, lines.join('\n'));
  console.log(`Wrote ${reportPath}`);
  console.log(`Raw disagreement rate: ${rawDisagreementRate}%`);
  console.log(`True disagreement rate: ${trueDisagreementRate}%`);
}

main();
