const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const srcRoot = path.join(repoRoot, 'frontend', 'src');

const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(srcRoot, 'lib', 'optime-v2-engine.ts'));

const {
  CARE_TYPES,
  loadBackendFacilities,
  toSearchFacility,
  emptyState,
} = simulationHelpers;

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

function contributorText(rows) {
  if (!rows || rows.length === 0) return 'None';
  return rows.map((row) => `${row.signal} (${row.scoreContribution})`).join('; ');
}

function weightMap(activeWeights) {
  return new Map(activeWeights.map((item) => [item.label, item.weight]));
}

function careTypeDistribution(recommendations) {
  const top10 = recommendations.slice(0, 10);
  return CARE_TYPES.map((type) => {
    const count = top10.filter((item) => item.facility.careTypes.includes(type)).length;
    return [type, `${Math.round((count / Math.max(1, top10.length)) * 100)}%`, count];
  });
}

function baseState(overrides = {}) {
  return emptyState({
    relationship: 'Parent',
    gender: 'Female',
    ageGroup: '80-84',
    budget: 10000,
    ...overrides,
  });
}

function buildPersonas() {
  return [
    {
      id: 'P1',
      name: 'Independent social widow',
      state: baseState({
        assistanceLevel: 'Fully independent',
        budget: 11000,
        notes: 'Widow living alone for several years, highly social, values community and movies.',
        happinessPreferences: ['Movies', 'Social activities', 'Group dining'],
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          socialProfile: {
            livingAloneDuration: '6 years',
            socialInteractionFrequency: 'Daily',
            newFriendsImportance: 'High',
            hobbyParticipation: ['Movies', 'Group dining'],
            preferredSocialIntensity: 'High',
          },
          familyProfile: {
            ...emptyState().humanIntelligenceV2.familyProfile,
            visitFrequencyExpectation: 'Weekly',
          },
          distanceProfile: {
            ...emptyState().humanIntelligenceV2.distanceProfile,
            driveTimes: { normal: '20', rushHour: '', emergency: '' },
            familyVisitExpectation: 'Weekly',
          },
          transitionRiskProfile: {
            ...emptyState().humanIntelligenceV2.transitionRiskProfile,
            lonelinessRisk: 'High',
          },
        },
      }),
      advisor: {
        priorities: ['Social Fit', 'Lifestyle Fit', 'Family Fit', 'Care Fit'],
        preferredCareTypes: ['Independent Living', 'Active Adult 55+', 'CCRC'],
        excludedCareTypes: ['Skilled Nursing', 'Rehabilitation', 'Hospice'],
      },
    },
    {
      id: 'P2',
      name: 'Independent introverted couple',
      state: baseState({
        relationship: 'Couple',
        assistanceLevel: 'Fully independent',
        budget: 14000,
        notes: 'Independent couple seeking privacy and quiet routines.',
        happinessPreferences: ['Quiet time', 'Reading'],
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          socialProfile: {
            livingAloneDuration: '',
            socialInteractionFrequency: 'Monthly or less',
            newFriendsImportance: 'Low',
            hobbyParticipation: ['Reading'],
            preferredSocialIntensity: 'Low',
          },
          familyProfile: {
            ...emptyState().humanIntelligenceV2.familyProfile,
            visitFrequencyExpectation: 'Monthly',
          },
          personalityProfile: {
            introvertExtrovert: 'Introverted',
            communitySizePreference: 'Small',
            privacyImportance: 'High',
            structureFlexibilityPreference: 'Flexible',
          },
        },
      }),
      advisor: {
        priorities: ['Lifestyle Fit', 'Care Fit', 'Financial Fit'],
        preferredCareTypes: ['Independent Living', 'CCRC', 'Active Adult 55+'],
        excludedCareTypes: ['Skilled Nursing', 'Rehabilitation'],
      },
    },
    {
      id: 'P3',
      name: 'Early memory concerns',
      state: baseState({
        assistanceLevel: 'Some daily support',
        memoryStatus: 'Mild memory issues',
        budget: 12000,
        notes: 'Needs medication reminders and gentle memory support.',
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          familyProfile: {
            ...emptyState().humanIntelligenceV2.familyProfile,
            involvedFamilyMembers: '3-4',
            visitFrequencyExpectation: 'Daily',
          },
          distanceProfile: {
            ...emptyState().humanIntelligenceV2.distanceProfile,
            driveTimes: { normal: '15', rushHour: '', emergency: '' },
            familyVisitExpectation: 'Daily',
          },
        },
      }),
      advisor: {
        priorities: ['Care Fit', 'Clinical Quality', 'Family Fit'],
        preferredCareTypes: ['Memory Care', 'Assisted Living'],
        excludedCareTypes: ['Independent Living', 'Active Adult 55+'],
      },
    },
    {
      id: 'P4',
      name: 'Assisted living transition',
      state: baseState({
        assistanceLevel: 'Some daily support',
        budget: 9500,
        notes: 'Transitioning from home and needs meals and daily support.',
        happinessPreferences: ['Group dining'],
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          familyProfile: {
            ...emptyState().humanIntelligenceV2.familyProfile,
            visitFrequencyExpectation: 'Several times weekly',
          },
        },
      }),
      advisor: {
        priorities: ['Care Fit', 'Family Fit', 'Lifestyle Fit'],
        preferredCareTypes: ['Assisted Living', 'CCRC'],
        excludedCareTypes: ['Skilled Nursing', 'Hospice'],
      },
    },
    {
      id: 'P5',
      name: 'Skilled nursing needs',
      state: baseState({
        assistanceLevel: 'Skilled nursing care',
        budget: 15000,
        notes: 'Requires skilled nursing oversight.',
      }),
      advisor: {
        priorities: ['Care Fit', 'Clinical Quality', 'Family Fit'],
        preferredCareTypes: ['Skilled Nursing', 'Rehabilitation'],
        excludedCareTypes: ['Independent Living', 'Active Adult 55+'],
      },
    },
    {
      id: 'P6',
      name: 'Rehabilitation after hospitalization',
      state: baseState({
        assistanceLevel: 'Skilled nursing care',
        budget: 15000,
        notes: 'Recent hospitalization and post-acute rehab needs. rehab therapy recovery',
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          transitionRiskProfile: {
            ...emptyState().humanIntelligenceV2.transitionRiskProfile,
            recentHospitalization: 'Yes',
            postHospitalRehabNeed: 'Yes',
          },
        },
      }),
      advisor: {
        priorities: ['Clinical Quality', 'Care Fit', 'Family Fit'],
        preferredCareTypes: ['Rehabilitation', 'Skilled Nursing'],
        excludedCareTypes: ['Independent Living'],
      },
    },
    {
      id: 'P7',
      name: 'Spanish speaking senior',
      state: baseState({
        assistanceLevel: 'Fully independent',
        budget: 10500,
        notes: 'Spanish-speaking senior seeking familiar language support.',
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          languageProfile: {
            ...emptyState().humanIntelligenceV2.languageProfile,
            preferredSpokenLanguage: 'Spanish',
            nativeLanguage: 'Spanish',
            medicalDiscussionLanguage: 'Spanish',
            socialInteractionLanguage: 'Spanish',
            languagesUnderstood: ['Spanish', 'English'],
            bilingualStaffRequired: 'Yes',
          },
          familyProfile: {
            ...emptyState().humanIntelligenceV2.familyProfile,
            visitFrequencyExpectation: 'Weekly',
          },
        },
      }),
      advisor: {
        priorities: ['Cultural Fit', 'Care Fit', 'Social Fit'],
        preferredCareTypes: ['Independent Living', 'CCRC', 'Assisted Living'],
        excludedCareTypes: ['Skilled Nursing', 'Rehabilitation'],
      },
    },
    {
      id: 'P8',
      name: 'Jewish senior seeking Jewish programming',
      state: baseState({
        assistanceLevel: 'Fully independent',
        budget: 12500,
        notes: 'Wants Jewish programming, community, and cultural familiarity.',
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          culturalProfile: {
            ...emptyState().humanIntelligenceV2.culturalProfile,
            religionImportance: 'High',
            faithTraditions: ['Jewish'],
            culturalIdentity: 'Jewish',
            whatFeelsLikeHome: ['Jewish community', 'Jewish programming'],
          },
          familyProfile: {
            ...emptyState().humanIntelligenceV2.familyProfile,
            visitFrequencyExpectation: 'Weekly',
          },
        },
      }),
      advisor: {
        priorities: ['Cultural Fit', 'Lifestyle Fit', 'Family Fit'],
        preferredCareTypes: ['Independent Living', 'CCRC', 'Assisted Living'],
        excludedCareTypes: ['Skilled Nursing', 'Rehabilitation'],
      },
    },
    {
      id: 'P9',
      name: 'Family-centered senior',
      state: baseState({
        assistanceLevel: 'Fully independent',
        budget: 11000,
        notes: 'Large family involvement and frequent visits matter most.',
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          familyProfile: {
            ...emptyState().humanIntelligenceV2.familyProfile,
            involvedFamilyMembers: '5+',
            visitFrequencyExpectation: 'Daily',
            grandchildrenImportance: 'High',
          },
          distanceProfile: {
            ...emptyState().humanIntelligenceV2.distanceProfile,
            driveTimes: { normal: '10', rushHour: '', emergency: '' },
            familyVisitExpectation: 'Daily',
          },
        },
      }),
      advisor: {
        priorities: ['Family Fit', 'Care Fit', 'Social Fit'],
        preferredCareTypes: ['Independent Living', 'CCRC', 'Assisted Living'],
        excludedCareTypes: ['Skilled Nursing', 'Rehabilitation'],
      },
    },
    {
      id: 'P10',
      name: 'High clinical complexity senior',
      state: baseState({
        assistanceLevel: 'Skilled nursing care',
        budget: 16000,
        notes: 'High acuity medical complexity and constant oversight required. High clinical complexity with frequent medical monitoring.',
        memoryStatus: 'Mild memory issues',
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          transitionRiskProfile: {
            ...emptyState().humanIntelligenceV2.transitionRiskProfile,
            recentHospitalization: 'Yes',
            postHospitalRehabNeed: 'Yes',
          },
        },
      }),
      advisor: {
        priorities: ['Clinical Quality', 'Care Fit', 'Family Fit'],
        preferredCareTypes: ['Skilled Nursing', 'Memory Care', 'Rehabilitation'],
        excludedCareTypes: ['Independent Living', 'Active Adult 55+'],
      },
    },
  ];
}

function advisorPriorityBonuses(priorityScores, priorities) {
  const keyByLabel = {
    'Care Fit': 'careFit',
    'Lifestyle Fit': 'lifestyleFit',
    'Social Fit': 'socialFit',
    'Cultural Fit': 'culturalFit',
    'Family Fit': 'familyFit',
    'Financial Fit': 'financialFit',
    'Clinical Quality': 'clinicalQuality',
    'Luxury Amenities': 'luxuryAmenities',
  };
  const multipliers = [0.18, 0.14, 0.1, 0.07];
  return priorities.reduce((sum, label, index) => {
    const key = keyByLabel[label];
    return sum + (key ? (priorityScores[key] * (multipliers[index] || 0.05)) : 0);
  }, 0);
}

function advisorCareTypeAdjustment(careTypes, preferredCareTypes, excludedCareTypes) {
  let score = 0;
  preferredCareTypes.forEach((type, index) => {
    if (careTypes.includes(type)) score += [20, 14, 10, 8][index] || 6;
  });
  excludedCareTypes.forEach((type, index) => {
    if (careTypes.includes(type)) score -= [28, 22, 16, 10][index] || 8;
  });
  return score;
}

function buildAdvisorTop5(engineOutput, advisorProfile) {
  const pool = engineOutput.accepted.length > 0 ? engineOutput.accepted.slice(0, 10) : engineOutput.rejected.slice(0, 10);
  const rescored = pool.map((item) => ({
    item,
    advisorScore:
      item.totalScore * 4 +
      advisorPriorityBonuses(item.priorityScores, advisorProfile.priorities) +
      advisorCareTypeAdjustment(item.facility.careTypes, advisorProfile.preferredCareTypes, advisorProfile.excludedCareTypes),
  }));

  return rescored
    .sort((left, right) => right.advisorScore - left.advisorScore)
    .slice(0, 5)
    .map((entry) => entry.item);
}

function agreementPercentage(optimeTop5, advisorTop5) {
  const advisorIds = new Set(advisorTop5.map((item) => item.facility.id));
  const overlap = optimeTop5.filter((item) => advisorIds.has(item.facility.id)).length;
  return Math.round((overlap / 5) * 100);
}

function benchmarkStatus(agreement) {
  if (agreement >= 90) return 'PASS';
  if (agreement >= 75) return 'GOOD';
  if (agreement >= 60) return 'NEEDS TUNING';
  return 'FAIL';
}

function highestWeightDifference(item) {
  const top = [...item.report.activeWeights].sort((left, right) => right.weight - left.weight)[0];
  return top ? `${top.label} (${Math.round(top.weight * 100)}%)` : 'No dominant weight';
}

function disagreementRows(optimeTop5, advisorTop5, advisorProfile) {
  const advisorIds = new Set(advisorTop5.map((item) => item.facility.id));
  return optimeTop5
    .filter((item) => !advisorIds.has(item.facility.id))
    .map((item) => {
      const selectedBecause = contributorText(item.report.positiveContributors);
      const likelyWouldNot = item.facility.careTypes.some((type) => advisorProfile.excludedCareTypes.includes(type))
        ? `Advisor excludes ${item.facility.careTypes.filter((type) => advisorProfile.excludedCareTypes.includes(type)).join(', ')} for this persona.`
        : `Advisor would prioritize ${advisorProfile.preferredCareTypes.join(', ')} over ${item.facility.careTypes.join(', ')}.`;
      const weightCause = highestWeightDifference(item);
      const calibration = item.facility.careTypes.some((type) => advisorProfile.excludedCareTypes.includes(type))
        ? 'Increase exclusion penalty for this care type under the persona-specific advisor model.'
        : 'Increase preferred care-type bonus or reduce non-core fit influence for this persona.';
      return [item.facility.name, selectedBecause, likelyWouldNot, weightCause, calibration];
    });
}

function buildBenchmarkResults(facilities, personas) {
  return personas.map((persona) => {
    const engineOutput = runOptimeV2Engine(facilities, persona.state);
    const optimeTop10 = engineOutput.accepted.slice(0, 10);
    const optimeTop5 = optimeTop10.slice(0, 5);
    const advisorTop5 = buildAdvisorTop5(engineOutput, persona.advisor);
    const agreement = agreementPercentage(optimeTop5, advisorTop5);
    return {
      persona,
      engineOutput,
      optimeTop10,
      optimeTop5,
      advisorTop5,
      distribution: careTypeDistribution(optimeTop10),
      agreement,
      status: benchmarkStatus(agreement),
      disagreements: disagreementRows(optimeTop5, advisorTop5, persona.advisor),
    };
  });
}

function buildMarkdown(results) {
  const averageAgreement = Math.round(results.reduce((sum, result) => sum + result.agreement, 0) / Math.max(1, results.length));
  const overallStatus = benchmarkStatus(averageAgreement);
  const comparisonRows = results.map((result) => [
    result.persona.name,
    result.optimeTop5.map((item) => item.facility.name).join('; '),
    result.advisorTop5.map((item) => item.facility.name).join('; '),
    `${result.agreement}%`,
    result.disagreements.length > 0 ? result.disagreements.map((row) => row[0]).join('; ') : 'None',
  ]);

  const sections = [];
  sections.push('# Human Advisor Benchmark V1');
  sections.push('');
  sections.push(`Benchmark Status: **${overallStatus}**`);
  sections.push(`Average Agreement: **${averageAgreement}%**`);
  sections.push('');
  sections.push('## Comparison');
  sections.push('');
  sections.push(markdownTable(['Persona', 'OPTIME Top 5', 'Advisor Expected Top 5', 'Agreement %', 'Disagreement Reasons'], comparisonRows));
  sections.push('');

  results.forEach((result) => {
    sections.push(`## ${result.persona.name}`);
    sections.push('');
    sections.push(`Generated Persona Type: **${result.engineOutput.persona.personaType}**`);
    sections.push('');
    sections.push('### Dynamic Weights');
    sections.push('');
    sections.push(markdownTable(['Dimension', 'Weight'], result.engineOutput.persona.activeWeights.map((item) => [item.label, `${Math.round(item.weight * 100)}%`])));
    sections.push('');
    sections.push('### OPTIME Top 10');
    sections.push('');
    sections.push(markdownTable(['Rank', 'Community', 'Care Types', 'Score'], result.optimeTop10.map((item, index) => [index + 1, item.facility.name, item.facility.careTypes.join(', '), item.totalScore.toFixed(2)])));
    sections.push('');
    sections.push('### Score Explanation');
    sections.push('');
    sections.push(result.optimeTop5[0] ? `${result.optimeTop5[0].report.rankingExplanation} ${result.optimeTop5[0].report.humanNarrativeExplanation}` : 'No recommendation available.');
    sections.push('');
    sections.push('### Care Type Distribution');
    sections.push('');
    sections.push(markdownTable(['Care Type', 'Top 10 Share', 'Count'], result.distribution));
    sections.push('');
    sections.push('### Advisor Simulation');
    sections.push('');
    sections.push(`Expected priorities: ${result.persona.advisor.priorities.join(', ')}`);
    sections.push(`Expected exclusions: ${result.persona.advisor.excludedCareTypes.join(', ')}`);
    sections.push('');
    sections.push(markdownTable(['Advisor Rank', 'Community', 'Care Types'], result.advisorTop5.map((item, index) => [index + 1, item.facility.name, item.facility.careTypes.join(', ')])));
    sections.push('');
    sections.push(`Agreement: **${result.agreement}%** (${result.status})`);
    sections.push('');
    sections.push('### Top Positive Contributors');
    sections.push('');
    sections.push(result.optimeTop5[0] ? contributorText(result.optimeTop5[0].report.positiveContributors) : 'None');
    sections.push('');
    sections.push('### Top Negative Contributors');
    sections.push('');
    sections.push(result.optimeTop5[0] ? contributorText(result.optimeTop5[0].report.negativeContributors) : 'None');
    sections.push('');
    sections.push('### Disagreements');
    sections.push('');
    if (result.disagreements.length === 0) {
      sections.push('No disagreements in the top 5.');
    } else {
      sections.push(markdownTable(['Community', 'Why OPTIME selected it', 'Why advisor likely would not', 'Weight caused difference', 'Suggested calibration'], result.disagreements));
    }
    sections.push('');
  });

  return { averageAgreement, overallStatus, markdown: sections.join('\n') };
}

function buildCsv(results) {
  const headers = ['persona', 'generated_persona_type', 'optime_top5', 'advisor_top5', 'agreement_percent', 'status', 'disagreement_communities', 'disagreement_reasons'];
  const rows = results.map((result) => [
    result.persona.name,
    result.engineOutput.persona.personaType,
    result.optimeTop5.map((item) => item.facility.name).join(' | '),
    result.advisorTop5.map((item) => item.facility.name).join(' | '),
    result.agreement,
    result.status,
    result.disagreements.map((row) => row[0]).join(' | ') || 'None',
    result.disagreements.map((row) => row[2]).join(' | ') || 'None',
  ]);
  return [headers, ...rows].map((row) => row.map(csvEscape).join(',')).join('\n');
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const personas = buildPersonas();
  const results = buildBenchmarkResults(facilities, personas);
  const { averageAgreement, overallStatus, markdown } = buildMarkdown(results);
  const csv = buildCsv(results);

  const markdownPath = path.join(repoRoot, 'reports', 'human_advisor_benchmark.md');
  const csvPath = path.join(repoRoot, 'reports', 'human_advisor_benchmark.csv');
  fs.writeFileSync(markdownPath, markdown);
  fs.writeFileSync(csvPath, csv);

  console.log(`Wrote ${markdownPath}`);
  console.log(`Wrote ${csvPath}`);
  console.log(`Average agreement: ${averageAgreement}%`);
  console.log(`Benchmark status: ${overallStatus}`);
  console.log(markdown);

  if (overallStatus !== 'PASS') {
    process.exitCode = 1;
  }
}

main();
