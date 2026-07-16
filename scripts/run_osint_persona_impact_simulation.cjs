const path = require('path');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');
const { loadBackendFacilities, toSearchFacility, emptyState } = simulationHelpers;
const { runOptimeV2Engine } = require(path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts'));

function cloneWithoutIntelligence(facility) {
  return {
    ...facility,
    intelligenceSnapshot: undefined,
  };
}

function personas() {
  return [
    {
      name: 'Independent social senior',
      state: emptyState({
        assistanceLevel: 'Fully independent',
        happinessPreferences: ['Movies', 'Social activities'],
        budget: 11000,
        humanIntelligenceV2: {
          ...emptyState().humanIntelligenceV2,
          socialProfile: {
            livingAloneDuration: '6 years',
            socialInteractionFrequency: 'Daily',
            newFriendsImportance: 'High',
            hobbyParticipation: ['Movies', 'Social activities'],
            preferredSocialIntensity: 'High',
          },
        },
      }),
    },
    {
      name: 'Early memory senior',
      state: emptyState({
        assistanceLevel: 'Some daily support',
        memoryStatus: 'Mild memory issues',
        budget: 12000,
      }),
    },
    {
      name: 'Rehabilitation senior',
      state: emptyState({
        assistanceLevel: 'Skilled nursing care',
        notes: 'rehab post-hospital recovery',
        budget: 15000,
      }),
    },
  ];
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const withIntelligence = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const withoutIntelligence = withIntelligence.map(cloneWithoutIntelligence);

  const results = personas().map((persona) => {
    const withOsint = runOptimeV2Engine(withIntelligence, persona.state, { mode: 'simulation' });
    const withoutOsint = runOptimeV2Engine(withoutIntelligence, persona.state, { mode: 'simulation' });
    const topWith = withOsint.accepted[0]?.facility.id;
    const topWithout = withoutOsint.accepted[0]?.facility.id;
    return {
      name: persona.name,
      changed: topWith !== topWithout || JSON.stringify(withOsint.accepted.slice(0, 5).map((item) => item.facility.id)) !== JSON.stringify(withoutOsint.accepted.slice(0, 5).map((item) => item.facility.id)),
      topWith: withOsint.accepted[0]?.facility.name || 'None',
      topWithout: withoutOsint.accepted[0]?.facility.name || 'None',
    };
  });

  const changedCount = results.filter((item) => item.changed).length;
  const status = changedCount >= 1 ? 'PASS' : 'FAIL';

  console.log(`OSINT Persona Impact Status: ${status}`);
  results.forEach((item) => {
    console.log(`${item.name}: ${item.changed ? 'changed' : 'unchanged'} | with OSINT=${item.topWith} | without OSINT=${item.topWithout}`);
  });

  if (status !== 'PASS') {
    process.exitCode = 1;
  }
}

main();
