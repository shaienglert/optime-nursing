const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function buildScenarioState() {
  const base = simulationHelpers.emptyState();
  return {
    ...base,
    relationship: 'Father',
    gender: 'Male',
    ageGroup: '80-84',
    assistanceLevel: 'Skilled nursing care',
    futureCarePreference: 'Full continuum of care on one campus',
    budget: 12000,
    happinessPreferences: ['Movies', 'Music activities'],
    referenceLocationType: 'County',
    referenceLocationValue: 'Miami-Dade County',
    notes: [
      'Male age 80.',
      'Requires 24/7 nursing support.',
      'Uses walker.',
      'Significant mobility limitations.',
      'History of stroke.',
      'Difficulty speaking after stroke.',
      'Requires gluten-free meals.',
      'Prefers full medical continuum.',
      'Move-in within 30-60 days.',
      'Preferred location Miami-Dade County.',
    ].join(' '),
    humanIntelligenceV2: {
      ...base.humanIntelligenceV2,
      foodProfile: {
        dietaryPreferences: ['Gluten-free'],
      },
      socialProfile: {
        ...base.humanIntelligenceV2.socialProfile,
        socialInteractionFrequency: 'Several times weekly',
      },
      transitionRiskProfile: {
        ...base.humanIntelligenceV2.transitionRiskProfile,
        recentHospitalization: 'Yes',
        postHospitalRehabNeed: 'Yes',
      },
      futureCareProfile: {
        ...base.humanIntelligenceV2.futureCareProfile,
        continuumOfCarePreference: 'Very important',
      },
      distanceProfile: {
        ...base.humanIntelligenceV2.distanceProfile,
        driveTimes: {
          normal: '30',
          rushHour: '45',
          emergency: '20',
        },
        familyVisitExpectation: 'Weekly',
      },
    },
  };
}

function toRows(topRecommendations) {
  return topRecommendations.map((item, index) => {
    const reasoning = item.rankReason || item.report.rankingExplanation || 'No rank reason available';
    return {
      rank: index + 1,
      facility_id: item.facility.id,
      facility_name: item.facility.name,
      total_score: Number(item.totalScore.toFixed(2)),
      final_match_score: item.report.finalMatchScore,
      confidence_score: item.report.confidenceScore,
      verified_count: item.report.audit.clinicalReasoning.verifiedCapabilities.length,
      unknown_count: item.report.audit.verificationRequest.unknownCount,
      hard_rejection_reasons: item.hardRejectionReasons,
      top_positive_contributors: item.report.positiveContributors.map((entry) => `${entry.signal} (${entry.scoreContribution})`),
      top_negative_contributors: item.report.negativeContributors.map((entry) => `${entry.signal} (${entry.scoreContribution})`),
      rank_reason: reasoning,
      traceability: item.report.scoreTraceability,
    };
  });
}

function toMarkdown(rows, meta) {
  const tableRows = rows.map((row) => [
    row.rank,
    row.facility_name,
    row.total_score,
    row.final_match_score,
    row.confidence_score,
    row.verified_count,
    row.unknown_count,
    row.rank_reason,
  ]);

  const lines = [];
  lines.push('# Top-5 Decision Table Report');
  lines.push('');
  lines.push(`Generated At (UTC): ${meta.generated_at_utc}`);
  lines.push(`Scenario Id: ${meta.scenario_id}`);
  lines.push(`Persona Type: ${meta.persona_type}`);
  lines.push('');
  lines.push('## Top-5 Table');
  lines.push('');
  lines.push(markdownTable(
    ['Rank', 'Facility', 'Total Score', 'Final Match Score', 'Confidence', 'Verified Requirements', 'Unknown Requirements', 'Rank Reason'],
    tableRows,
  ));
  lines.push('');
  lines.push('## Governance Notes');
  lines.push('');
  lines.push('- Only accepted candidates are included.');
  lines.push('- UNKNOWN values remain explicit and are not converted to rejection by default.');
  lines.push('- Rank reasons are taken from engine ranking explanation output.');
  lines.push('');
  lines.push('## Mechanical Output Summary');
  lines.push('');
  lines.push(`- accepted_count: ${meta.accepted_count}`);
  lines.push(`- rejected_count: ${meta.rejected_count}`);
  lines.push(`- displayed_count: ${meta.displayed_count}`);
  return lines.join('\n');
}

function main() {
  const facilities = simulationHelpers.loadBackendFacilities().map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));
  const state = buildScenarioState();
  const output = runOptimeV2Engine(facilities, state);

  if (!output.accepted || output.accepted.length === 0) {
    throw new Error('No accepted recommendations produced; cannot build top-5 decision table.');
  }

  const top5 = output.accepted.slice(0, 5);
  const rows = toRows(top5);

  const meta = {
    generated_at_utc: new Date().toISOString(),
    scenario_id: 'PHASE6_TOP5_BASELINE',
    persona_type: output.persona.personaType,
    accepted_count: output.accepted.length,
    rejected_count: output.rejected.length,
    displayed_count: output.displayedRecommendations.length,
  };

  const payload = {
    phase: 6,
    meta,
    rows,
  };

  const jsonPath = path.join(repoRoot, 'database', 'top5_decision_table.json');
  const mdPath = path.join(repoRoot, 'reports', 'TOP5_DECISION_TABLE_REPORT.md');
  fs.writeFileSync(jsonPath, JSON.stringify(payload, null, 2));
  fs.writeFileSync(mdPath, toMarkdown(rows, meta));

  console.log(`WROTE=${jsonPath}`);
  console.log(`WROTE=${mdPath}`);
  console.log(`TOP5_COUNT=${rows.length}`);
  console.log(`PERSONA_TYPE=${meta.persona_type}`);
}

main();
