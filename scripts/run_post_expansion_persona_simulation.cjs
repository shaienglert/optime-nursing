const path = require('path');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

const PRIMARY_CATEGORIES = [
  'Active Adult 55+',
  'Independent Living',
  'Assisted Living',
  'Memory Care',
  'Skilled Nursing',
  'Rehabilitation',
  'CCRC',
];

function primaryCategory(facility) {
  const probabilities = facility.careTypeProbabilities || {};
  const ranked = PRIMARY_CATEGORIES
    .map((category) => ({ category, probability: Number(probabilities[category] || 0) }))
    .sort((a, b) => b.probability - a.probability);
  if (ranked[0] && ranked[0].probability > 0) return ranked[0].category;
  return (facility.careTypes || [])[0] || 'UNKNOWN';
}

function buildState() {
  const base = simulationHelpers.emptyState();
  return {
    ...base,
    assistanceLevel: 'Fully independent',
    futureCarePreference: 'Independent today, support available later',
    budget: 11800,
    happinessPreferences: ['Movies', 'Music activities', 'Outdoor activities'],
    referenceLocationType: 'City',
    referenceLocationValue: 'Miami area',
    notes: [
      'Fully independent now.',
      'Support available later is preferred.',
      'Kitchenette required.',
      'Outdoor activities preferred.',
      'Miami area strongly preferred.',
    ].join(' '),
    humanIntelligenceV2: {
      ...base.humanIntelligenceV2,
      socialProfile: {
        ...base.humanIntelligenceV2.socialProfile,
        socialInteractionFrequency: 'Several times weekly',
        hobbyParticipation: ['Movies', 'Music activities', 'Outdoor activities'],
      },
      lifestyleProfile: {
        ...base.humanIntelligenceV2.lifestyleProfile,
        desiredAmenities: ['Kitchenette', 'Outdoor space', 'Movie activities', 'Music activities'],
      },
      futureCareProfile: {
        ...base.humanIntelligenceV2.futureCareProfile,
        continuumOfCarePreference: 'Important',
      },
      distanceProfile: {
        ...base.humanIntelligenceV2.distanceProfile,
        preferredRadiusMiles: 20,
      },
    },
  };
}

function main() {
  const facilities = simulationHelpers
    .loadBackendFacilities()
    .map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));

  const state = buildState();
  const output = runOptimeV2Engine(facilities, state, { mode: 'simulation' });
  const top10 = output.accepted.slice(0, 10).map((item, index) => ({
    rank: index + 1,
    name: item.facility.name,
    score: item.totalScore,
    primaryCategory: primaryCategory(item.facility),
    careTypes: item.facility.careTypes.join('; '),
    city: item.facility.city || 'UNKNOWN',
  }));

  const categoryCounts = top10.reduce((acc, item) => {
    acc[item.primaryCategory] = (acc[item.primaryCategory] || 0) + 1;
    return acc;
  }, {});

  console.log('TOP_10_POST_EXPANSION_SIMULATION');
  top10.forEach((item) => {
    console.log([
      item.rank,
      item.name,
      item.score,
      item.primaryCategory,
      item.careTypes,
      item.city,
    ].join(' | '));
  });

  console.log(`TOTAL_ACCEPTED=${output.accepted.length}`);
  console.log(`TOP10_REHABILITATION_COUNT=${categoryCounts.Rehabilitation || 0}`);
  console.log(`TOP10_INDEPENDENT_ASSISTED_CCRC_COUNT=${(categoryCounts['Independent Living'] || 0) + (categoryCounts['Assisted Living'] || 0) + (categoryCounts.CCRC || 0)}`);
}

main();
