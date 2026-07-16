const fs = require('fs');
const path = require('path');
const Module = require('module');
const ts = require(path.join(__dirname, '..', 'frontend', 'node_modules', 'typescript'));
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');
const frontendRoot = path.join(repoRoot, 'frontend');
const srcRoot = path.join(frontendRoot, 'src');

const originalResolveFilename = Module._resolveFilename;
Module._resolveFilename = function resolveFilename(request, parent, isMain, options) {
  if (request.startsWith('@/')) {
    request = path.join(srcRoot, request.slice(2));
  }
  return originalResolveFilename.call(this, request, parent, isMain, options);
};

function registerTypeScriptExtension(ext) {
  require.extensions[ext] = (module, filename) => {
    const source = fs.readFileSync(filename, 'utf8');
    const output = ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
      fileName: filename,
    });
    module._compile(output.outputText, filename);
  };
}

registerTypeScriptExtension('.ts');
registerTypeScriptExtension('.tsx');

const { runOptimeV2Engine } = require(path.join(srcRoot, 'lib', 'optime-v2-engine.ts'));

const CARE_TYPES = [
  'Independent Living',
  'Active Adult 55+',
  'Assisted Living',
  'Memory Care',
  'Skilled Nursing',
  'Rehabilitation',
  'CCRC',
  'Continuing Care',
  'Hospice',
  'UNKNOWN',
];

function loadBackendFacilities() {
  const dbPath = path.join(repoRoot, 'optime_nursing.db');
  const pythonCode = [
    'import json, sqlite3, sys',
    'conn = sqlite3.connect(sys.argv[1])',
    'conn.row_factory = sqlite3.Row',
    'cur = conn.cursor()',
    'rows = cur.execute("select id, cms_id, name, city, state, address, zip_code, phone, overall_rating, staffing_rating, quality_rating, inspection_rating, beds, medical_quality_score, staffing_score, safety_score, overall_optime_score, confidence_level from facilities where state = ? order by overall_optime_score desc, id asc", ("FL",)).fetchall()',
    'print(json.dumps([dict(row) for row in rows]))',
  ].join('\n');
  const result = spawnSync('python', ['-c', pythonCode, dbPath], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error(`Failed to query SQLite dataset. ${result.stderr || result.stdout}`.trim());
  }

  return JSON.parse(result.stdout);
}

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function parseConfidence(level) {
  if (String(level || '').toUpperCase() === 'HIGH') return 'HIGH';
  if (String(level || '').toUpperCase() === 'MEDIUM') return 'MEDIUM';
  if (String(level || '').toUpperCase() === 'LOW') return 'LOW';
  return 'UNKNOWN';
}

function combineConfidence(modelConfidence, careTypeConfidence) {
  const rank = { HIGH: 3, MEDIUM: 2, LOW: 1, UNKNOWN: 0 };
  return rank[careTypeConfidence] < rank[modelConfidence] ? careTypeConfidence : modelConfidence;
}

function makePriceRange(facility) {
  const base = facility.beds ? 3800 + Math.min(2200, facility.beds * 15) : 4200;
  const high = base + 2400;
  return `$${Math.round(base).toLocaleString()} - $${Math.round(high).toLocaleString()}/month`;
}

function scoreLabel(score) {
  if (score >= 90) return 'Excellent Match';
  if (score >= 80) return 'Great Match';
  if (score >= 70) return 'Good Match';
  return 'Consider Match';
}

function buildShortExplanation(facility) {
  const quality = Math.round(facility.medical_quality_score ?? 0);
  const staffing = Math.round(facility.staffing_score ?? 0);
  const safety = Math.round(facility.safety_score ?? 0);

  if (quality >= 85 && staffing >= 80) {
    return 'High-performing clinical and staffing profile with strong day-to-day support.';
  }

  if (safety >= 80) {
    return 'Safety and inspection indicators are strong for a more stable care environment.';
  }

  if ((facility.quality_rating ?? 0) >= 4 || (facility.overall_rating ?? 0) >= 4) {
    return 'Solid CMS-aligned quality performance with balanced medical and support signals.';
  }

  return 'Balanced option for families looking for practical care support at this budget range.';
}

function baseFacilityText(facility) {
  return [facility.name, facility.address, facility.city, buildShortExplanation(facility)].filter(Boolean).join(' ').toLowerCase();
}

function inferLegacyCareTaxonomy(facility) {
  const careTypes = ['Assisted Living'];
  if ((facility.quality_rating ?? 0) >= 4) careTypes.push('Skilled Nursing');
  if ((facility.inspection_rating ?? 0) >= 4) careTypes.push('Memory Care');
  return { careTypes, confidence: 'MEDIUM' };
}

function inferExplicitCareTaxonomy(facility) {
  const text = baseFacilityText(facility);
  const careTypes = new Set();
  let confidence = 'LOW';

  const add = (type, nextConfidence) => {
    careTypes.add(type);
    if (nextConfidence === 'HIGH' || (nextConfidence === 'MEDIUM' && confidence === 'LOW')) {
      confidence = nextConfidence;
    }
  };

  if (/\b(independent living|independent senior|senior living|retirement living)\b/.test(text)) {
    add('Independent Living', 'HIGH');
  }
  if (/\b(active adult|55\+|55 plus|55 and older)\b/.test(text)) {
    add('Active Adult 55+', 'HIGH');
  }
  if (/\b(assisted living|assistance with daily living|alf)\b/.test(text)) {
    add('Assisted Living', 'HIGH');
  }
  if (/\b(memory care|memory support|alzheim|dementia|memory neighborhood)\b/.test(text)) {
    add('Memory Care', 'HIGH');
  }
  if (/\b(rehab|rehabilitation|therapy|post-acute|recovery)\b/.test(text)) {
    add('Rehabilitation', 'HIGH');
  }
  if (/\b(skilled nursing|nursing home|convalescent|extended care|health and rehab|nursing and rehabilitation|rehab care center|care center)\b/.test(text)) {
    add('Skilled Nursing', 'HIGH');
  }
  if (/\b(continuing care|continuum of care|life plan)\b/.test(text)) {
    add('Continuing Care', 'HIGH');
  }
  if (/\b(ccrc|retirement community|retirement village|village)\b/.test(text)) {
    add('CCRC', careTypes.size === 0 ? 'MEDIUM' : 'HIGH');
  }
  if (/\b(hospice|palliative|end of life)\b/.test(text)) {
    add('Hospice', 'HIGH');
  }

  if ((careTypes.has('CCRC') || careTypes.has('Continuing Care')) && !careTypes.has('Independent Living')) {
    add('Independent Living', 'MEDIUM');
  }

  if (careTypes.size === 0) {
    return { careTypes: ['UNKNOWN'], confidence: 'LOW' };
  }

  return { careTypes: [...careTypes], confidence };
}

function makeBadges(facility, careTypes) {
  const badges = [];
  if (careTypes.some((type) => type !== 'UNKNOWN')) badges.push('Explicit care taxonomy');
  if ((facility.overall_rating ?? 0) >= 4) badges.push('Strong clinical quality');
  if ((facility.staffing_rating ?? 0) >= 4) badges.push('Staffing stability');
  if ((facility.quality_rating ?? 0) >= 4) badges.push('Medication support');
  if ((facility.inspection_rating ?? 0) >= 4) badges.push('Safety indicators strong');
  return badges;
}

function normalizeSearchText(value) {
  return String(value || '').normalize('NFKC').toLowerCase().trim();
}

function tokenizeSearchText(value) {
  return normalizeSearchText(value).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
}

const SEARCH_SYNONYMS = {
  hebrew: ['עברית', 'hebrew', 'יהודית'],
  jewish: ['יהודי', 'יהדות', 'jewish', 'synagogue', 'בית', 'כנסת'],
  kosher: ['כשר', 'kosher'],
  social: ['חברתי', 'social', 'active'],
  memory: ['זיכרון', 'memory', 'דמנציה'],
  wheelchair: ['נגיש', 'כיסא', 'גלגלים', 'wheelchair', 'accessible'],
  spanish: ['spanish', 'espanol', 'español'],
  catholic: ['catholic', 'church', 'mass'],
};

function expandSearchTerm(term) {
  const normalized = normalizeSearchText(term);
  const expansions = new Set([normalized]);
  Object.entries(SEARCH_SYNONYMS).forEach(([key, values]) => {
    if (key === normalized || values.includes(normalized)) {
      expansions.add(key);
      values.forEach((value) => expansions.add(normalizeSearchText(value)));
    }
  });
  return [...expansions];
}

function buildFacilitySearchTokens(base, careTypes = [], matchBadges = []) {
  const joined = [base.name, base.city || '', base.state || '', base.address || '', base.zip_code || '', ...careTypes, ...matchBadges].join(' ');
  const tokens = new Set(tokenizeSearchText(joined));
  tokenizeSearchText(joined).forEach((token) => {
    expandSearchTerm(token).forEach((expanded) => tokens.add(expanded));
  });
  return [...tokens];
}

function toFacility(facility) {
  const verificationScore = Math.max(30, Math.min(100, Math.round(facility.overall_optime_score ?? 70)));
  return {
    id: facility.id,
    cms_id: facility.cms_id,
    name: facility.name,
    city: facility.city,
    state: facility.state,
    overall_rating: facility.overall_rating ?? undefined,
    staffing_rating: facility.staffing_rating ?? undefined,
    beds: facility.beds ?? undefined,
    address: facility.address,
    zip_code: facility.zip_code,
    phone: facility.phone ?? null,
    quality_rating: facility.quality_rating ?? undefined,
    inspection_rating: facility.inspection_rating ?? undefined,
    latitude: null,
    longitude: null,
    verified_name: facility.name,
    license_verified: Boolean(facility.cms_id),
    cms_verified: Boolean(facility.cms_id),
    website_verified: false,
    phone_verified: Boolean(facility.phone),
    verification_score: verificationScore,
    matching_confidence: parseConfidence(facility.confidence_level),
  };
}

function toSearchFacility(facility, mode) {
  const base = toFacility(facility);
  const optimeScore = Math.round(facility.overall_optime_score ?? 70);
  const taxonomy = mode === 'legacy' ? inferLegacyCareTaxonomy(facility) : inferExplicitCareTaxonomy(facility);
  const result = {
    ...base,
    matching_confidence: combineConfidence(base.matching_confidence, taxonomy.confidence),
    imageUrl: '/placeholder.jpg',
    optimeScore,
    matchLabel: scoreLabel(optimeScore),
    shortExplanation: buildShortExplanation(facility),
    priceRange: makePriceRange(facility),
    careTypes: taxonomy.careTypes,
    careTypeConfidence: taxonomy.confidence,
    matchBadges: makeBadges(facility, taxonomy.careTypes),
    scoreBreakdown: [
      {
        category: 'Medical Quality',
        score: Math.round(facility.medical_quality_score ?? 0),
        explanation: 'Derived from CMS quality and event-rate metrics.',
        dataSource: ['CMS Quality', 'Inspections'],
      },
      {
        category: 'Staffing',
        score: Math.round(facility.staffing_score ?? 0),
        explanation: 'Derived from staffing hours and staffing quality metrics.',
        dataSource: ['CMS Staffing'],
      },
      {
        category: 'Safety',
        score: Math.round(facility.safety_score ?? 0),
        explanation: 'Derived from deficiencies, complaints, and inspection signals.',
        dataSource: ['CMS Inspections'],
      },
    ],
  };
  result.searchTokens = buildFacilitySearchTokens(base, result.careTypes, result.matchBadges);
  return result;
}

function emptyState(overrides = {}) {
  return {
    relationship: 'Parent',
    gender: 'Female',
    coupleAssistance: '',
    ageGroup: '80-84',
    assistanceLevel: '',
    memoryStatus: '',
    happinessPreferences: [],
    budget: 7000,
    distanceFromFamily: '',
    referenceLocationType: '',
    referenceLocationValue: '',
    notes: '',
    humanIntelligenceV2: {
      socialProfile: {
        livingAloneDuration: '',
        socialInteractionFrequency: '',
        newFriendsImportance: '',
        hobbyParticipation: [],
        preferredSocialIntensity: '',
      },
      familyProfile: {
        involvedFamilyMembers: '',
        visitFrequencyExpectation: '',
        grandchildrenPresence: '',
        grandchildrenImportance: '',
        familyDecisionDynamics: '',
        emergencySupportNetwork: '',
        coupleStayTogetherPreference: '',
        widowStatus: '',
        lossTiming: '',
        socialActivityChangeSinceLoss: '',
        socialInteractionNeed: '',
        temporarySeparationAcceptance: '',
        griefSupportInterest: '',
      },
      culturalProfile: {
        religionImportance: '',
        faithTraditions: [],
        religiousSupportNeeds: [],
        kosherRequirements: '',
        synagogueChurchAccess: '',
        holidayCelebrations: '',
        culturalIdentity: '',
        israeliJewishCommunityPreference: '',
        whatFeelsLikeHome: [],
        worshipAccessRequirement: '',
        jewishProgrammingImportance: '',
        churchAccessRequirement: '',
        christianServiceRequirement: '',
        halalMealsRequirement: '',
        prayerFacilityRequirement: '',
      },
      languageProfile: {
        preferredSpokenLanguage: '',
        nativeLanguage: '',
        medicalDiscussionLanguage: '',
        socialInteractionLanguage: '',
        languageNeedScope: '',
        languagesUnderstood: [],
        familyLanguages: [],
        bilingualStaffRequired: '',
      },
      foodProfile: {
        dietaryPreferences: [],
      },
      familyCultureProfile: {
        involvementExpectation: '',
        decisionRole: '',
      },
      communityPreferenceProfile: {
        preferredEnvironment: [],
      },
      personalityProfile: {
        introvertExtrovert: '',
        communitySizePreference: '',
        privacyImportance: '',
        structureFlexibilityPreference: '',
      },
      interestsProfile: [],
      independenceProfile: {
        drivingImportance: '',
        cookingImportance: '',
        abilityToLeaveIndependently: '',
        petOwnershipImportance: '',
        hostingFamilyImportance: '',
      },
      transitionRiskProfile: {
        biggestFear: '',
        attitudeTowardMove: '',
        previousMoves: '',
        bereavementStatus: '',
        lonelinessRisk: '',
        socialIsolationConcern: '',
        recentHospitalization: '',
        hospitalizationRecency: '',
        postHospitalRehabNeed: '',
        wanderingConcerns: '',
      },
      futureCareProfile: {
        agingInPlaceImportance: '',
        avoidFutureMovesPreference: '',
        continuumOfCarePreference: '',
        secureMemoryNeighborhoodNeed: '',
        familiarLanguageRequirement: '',
      },
      distanceProfile: {
        referenceLocations: {
          parentCurrentHome: '',
          primaryCaregiverHome: '',
          secondaryFamilyHomes: '',
          preferredHospital: '',
          placeOfWorship: '',
        },
        driveTimes: {
          normal: '',
          rushHour: '',
          emergency: '',
        },
        familyVisitExpectation: '',
        familyGeographyModel: {
          involvedFamilyMembers: '',
          familyCenterOfGravity: '',
          multiLocationOptimization: '',
        },
        emotionalDistanceFactors: {
          emergencyAccessImportance: '',
          spontaneousVisitsImportance: '',
          grandchildrenVisitsImportance: '',
        },
        careLevelWeight: 0,
        optimizationStrategy: '',
        scores: {
          family_distance_score: null,
          visit_probability_score: null,
          emergency_access_score: null,
          grandchildren_access_score: null,
          travel_burden_score: null,
          family_engagement_score: null,
        },
        inferredConfidence: {},
      },
      confidence: {},
      scoringEngine: {
        overallConfidence: 0,
        confidenceThreshold: 0,
        adaptiveSignals: [],
        scoringWeights: {},
        outputScores: {
          social_fit_score: 0,
          family_fit_score: 0,
          language_fit_score: 0,
          cultural_fit_score: 0,
          religious_fit_score: 0,
          food_fit_score: 0,
          family_engagement_score: 0,
          community_style_score: 0,
          independence_fit_score: 0,
          transition_success_probability: 0,
          loneliness_risk_score: 0,
        },
        recommendationImpacts: [],
        additionalQuestionAsked: '',
      },
    },
    ...overrides,
  };
}

function personaStates() {
  return {
    A: emptyState({
      ageGroup: '80-84',
      assistanceLevel: 'Fully independent',
      happinessPreferences: ['Movies', 'Social activities', 'Group dining'],
      budget: 11500,
      notes: 'Highly social and fully independent. Wants movies, social activities, and group dining.',
      humanIntelligenceV2: {
        ...emptyState().humanIntelligenceV2,
        socialProfile: {
          livingAloneDuration: '8 years',
          socialInteractionFrequency: 'Daily',
          newFriendsImportance: 'High',
          hobbyParticipation: ['Movies', 'Social activities', 'Group dining'],
          preferredSocialIntensity: 'High',
        },
        familyProfile: {
          ...emptyState().humanIntelligenceV2.familyProfile,
          involvedFamilyMembers: '3-4',
          visitFrequencyExpectation: 'Weekly',
        },
        distanceProfile: {
          ...emptyState().humanIntelligenceV2.distanceProfile,
          driveTimes: { normal: '25', rushHour: '', emergency: '' },
          familyVisitExpectation: 'Weekly',
        },
        transitionRiskProfile: {
          ...emptyState().humanIntelligenceV2.transitionRiskProfile,
          lonelinessRisk: 'High',
        },
      },
    }),
    B: emptyState({
      ageGroup: '80-84',
      assistanceLevel: 'Some daily support',
      memoryStatus: 'Mild memory issues',
      budget: 12000,
      notes: 'Early memory concerns and needs medication reminders.',
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
    C: emptyState({
      ageGroup: '75-79',
      assistanceLevel: 'Skilled nursing care',
      budget: 15000,
      notes: 'Recent hospitalization and needs rehabilitation. rehab post-hospital therapy',
      humanIntelligenceV2: {
        ...emptyState().humanIntelligenceV2,
        familyProfile: {
          ...emptyState().humanIntelligenceV2.familyProfile,
          visitFrequencyExpectation: 'Several times weekly',
        },
        distanceProfile: {
          ...emptyState().humanIntelligenceV2.distanceProfile,
          driveTimes: { normal: '20', rushHour: '', emergency: '' },
          familyVisitExpectation: 'Several times weekly',
        },
        transitionRiskProfile: {
          ...emptyState().humanIntelligenceV2.transitionRiskProfile,
          recentHospitalization: 'Yes',
          postHospitalRehabNeed: 'Yes',
        },
      },
    }),
    D: emptyState({
      ageGroup: '80-84',
      assistanceLevel: 'Fully independent',
      budget: 10000,
      happinessPreferences: ['Religious activities', 'Family gatherings'],
      notes: 'Spanish speaking, Catholic, large family involvement, fully independent.',
      humanIntelligenceV2: {
        ...emptyState().humanIntelligenceV2,
        socialProfile: {
          ...emptyState().humanIntelligenceV2.socialProfile,
          socialInteractionFrequency: 'Several times weekly',
          newFriendsImportance: 'Medium',
        },
        familyProfile: {
          ...emptyState().humanIntelligenceV2.familyProfile,
          involvedFamilyMembers: '5+',
          visitFrequencyExpectation: 'Daily',
          grandchildrenImportance: 'High',
        },
        culturalProfile: {
          ...emptyState().humanIntelligenceV2.culturalProfile,
          religionImportance: 'High',
          faithTraditions: ['Catholic'],
          culturalIdentity: 'Latino',
          whatFeelsLikeHome: ['Catholic community', 'Spanish speaking'],
          churchAccessRequirement: 'Required',
          christianServiceRequirement: 'Required',
        },
        languageProfile: {
          ...emptyState().humanIntelligenceV2.languageProfile,
          preferredSpokenLanguage: 'Spanish',
          nativeLanguage: 'Spanish',
          medicalDiscussionLanguage: 'Spanish',
          socialInteractionLanguage: 'Spanish',
          languageNeedScope: 'Daily life and care',
          languagesUnderstood: ['Spanish', 'English'],
          bilingualStaffRequired: 'Yes',
        },
        distanceProfile: {
          ...emptyState().humanIntelligenceV2.distanceProfile,
          driveTimes: { normal: '15', rushHour: '', emergency: '' },
          familyVisitExpectation: 'Daily',
        },
      },
    }),
  };
}

function percentage(part, total) {
  if (total <= 0) return '0%';
  return `${Math.round((part / total) * 100)}%`;
}

function careTypeDistribution(recommendations) {
  const top10 = recommendations.slice(0, 10);
  return CARE_TYPES.filter((type) => type !== 'UNKNOWN').map((type) => {
    const count = top10.filter((item) => item.facility.careTypes.includes(type)).length;
    return [type, percentage(count, top10.length), count];
  });
}

function weightMap(activeWeights) {
  return new Map(activeWeights.map((item) => [item.label, item.weight]));
}

function contributorText(rows) {
  if (!rows || rows.length === 0) return 'None';
  return rows.map((row) => `${row.signal} (${row.scoreContribution})`).join('; ');
}

function compareRanks(afterRecommendations, beforeRecommendations) {
  const beforeRank = new Map(beforeRecommendations.map((item, index) => [item.facility.id, index + 1]));
  return afterRecommendations.slice(0, 10).map((item, index) => {
    const legacyRank = beforeRank.get(item.facility.id) || 'NR';
    const delta = typeof legacyRank === 'number' ? legacyRank - (index + 1) : 'NR';
    return [item.facility.name, legacyRank, index + 1, delta, item.facility.careTypes.join(', ')];
  });
}

function analyzePersona(code, state, legacyFacilities, migratedFacilities) {
  const before = runOptimeV2Engine(legacyFacilities, state);
  const after = runOptimeV2Engine(migratedFacilities, state);
  const top = after.accepted[0];
  return {
    code,
    state,
    before,
    after,
    top,
    distribution: careTypeDistribution(after.accepted),
    beforeAfter: compareRanks(after.accepted, before.accepted),
    weights: after.persona.activeWeights,
    positiveContributors: top?.report.positiveContributors || [],
    negativeContributors: top?.report.negativeContributors || [],
  };
}

function personaVerdict(result) {
  const weights = weightMap(result.weights);
  const top5 = result.after.accepted.slice(0, 5);
  const top10 = result.after.accepted.slice(0, 10);
  const qualityPassed = result.after.qualityCheck.passed;
  const failures = [];

  if (result.code === 'A') {
    if (!((weights.get('Social Fit') || 0) > (weights.get('Lifestyle Fit') || 0) && (weights.get('Lifestyle Fit') || 0) > (weights.get('Care Fit') || 0))) {
      failures.push('Expected Social Fit > Lifestyle Fit > Care Fit.');
    }
    if (top5.some((item) => /nursing home/i.test(item.facility.name))) failures.push('Nursing Home appears in Top 5.');
    if (top5.some((item) => /rehab|rehabilitation/i.test(item.facility.name))) failures.push('Rehab center appears in Top 5.');
    const skilledNursingCount = top10.filter((item) => item.facility.careTypes.includes('Skilled Nursing')).length;
    if (skilledNursingCount > 5) failures.push('Skilled Nursing dominates Top 10.');
  }

  if (result.code === 'B') {
    if (!((weights.get('Care Fit') || 0) > (weights.get('Clinical Quality') || 0) && (weights.get('Clinical Quality') || 0) > (weights.get('Family Fit') || 0))) {
      failures.push('Expected Care Fit > Clinical Quality > Family Fit.');
    }
    const memoryTop5 = top5.filter((item) => item.facility.careTypes.includes('Memory Care')).length;
    if (memoryTop5 === 0) failures.push('Memory Care is absent from Top 5.');
    const independentTop5 = top5.filter((item) => item.facility.careTypes.includes('Independent Living')).length;
    if (independentTop5 >= 3) failures.push('Independent Living dominates early-memory results.');
  }

  if (result.code === 'C') {
    if (!((weights.get('Clinical Quality') || 0) > (weights.get('Care Fit') || 0))) {
      failures.push('Expected Clinical Quality > Care Fit.');
    }
    const firstIndependent = top10.findIndex((item) => item.facility.careTypes.includes('Independent Living'));
    const firstClinical = top10.findIndex((item) => item.facility.careTypes.includes('Rehabilitation') || item.facility.careTypes.includes('Skilled Nursing'));
    if (firstIndependent !== -1 && firstClinical !== -1 && firstIndependent < firstClinical) {
      failures.push('Independent Living appears above rehab-oriented facilities.');
    }
  }

  if (result.code === 'D') {
    if (!((weights.get('Cultural Fit') || 0) > (weights.get('Family Fit') || 0) && (weights.get('Family Fit') || 0) > (weights.get('Social Fit') || 0))) {
      failures.push('Expected Cultural Fit > Family Fit > Social Fit.');
    }
    if ((weights.get('Cultural Fit') || 0) < 0.15) failures.push('Cultural Fit contributes less than 15%.');
    const contributorBlob = `${contributorText(result.positiveContributors)} ${top10[0]?.report.humanNarrativeExplanation || ''}`.toLowerCase();
    if (!/spanish|catholic|cultural|language|faith/.test(contributorBlob)) {
      failures.push('Spanish or faith signals have no visible ranking impact.');
    }
  }

  if (!qualityPassed) {
    failures.push(`Quality gate failed: ${result.after.qualityCheck.failures.join(' | ')}`);
  }

  return {
    passed: failures.length === 0,
    failures,
  };
}

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

function buildCsv(results) {
  const headers = ['persona', 'phase', 'rank', 'community', 'care_types', 'score', 'persona_type', 'quality_gate_passed', 'quality_gate_failures', 'positive_contributors', 'negative_contributors'];
  const rows = [];
  results.forEach((result) => {
    [
      ['before', result.before],
      ['after', result.after],
    ].forEach(([phase, engineOutput]) => {
      engineOutput.accepted.slice(0, 10).forEach((item, index) => {
        rows.push([
          result.code,
          phase,
          index + 1,
          item.facility.name,
          item.facility.careTypes.join('; '),
          item.totalScore.toFixed(2),
          engineOutput.persona.personaType,
          engineOutput.qualityCheck.passed,
          engineOutput.qualityCheck.failures.join(' | '),
          contributorText(item.report.positiveContributors),
          contributorText(item.report.negativeContributors),
        ]);
      });
    });
  });
  return [headers, ...rows].map((row) => row.map(csvEscape).join(',')).join('\n');
}

function buildReport(results) {
  const verdicts = results.map((result) => ({ code: result.code, verdict: personaVerdict(result) }));
  const overallPass = verdicts.every((item) => item.verdict.passed);
  const sections = [];
  sections.push('# Post Taxonomy Validation Report');
  sections.push('');
  sections.push(`Verdict: **${overallPass ? 'PASS' : 'FAIL'}**`);
  sections.push('');
  sections.push('## Summary');
  sections.push('');
  verdicts.forEach((item) => {
    sections.push(`- Persona ${item.code}: **${item.verdict.passed ? 'PASS' : 'FAIL'}**${item.verdict.failures.length > 0 ? ` - ${item.verdict.failures.join(' ')}` : ''}`);
  });
  sections.push('');

  results.forEach((result) => {
    const verdict = verdicts.find((item) => item.code === result.code).verdict;
    sections.push(`## Persona ${result.code}`);
    sections.push('');
    sections.push(`Generated Persona Type: **${result.after.persona.personaType}**`);
    sections.push(`Quality Gate Status: **${result.after.qualityCheck.passed ? 'PASS' : 'FAIL'}**`);
    if (!result.after.qualityCheck.passed) {
      sections.push(`Quality Gate Failures: ${result.after.qualityCheck.failures.join(' | ')}`);
    }
    sections.push('');
    sections.push('### Top 10 Recommendations');
    sections.push('');
    sections.push(markdownTable(['Rank', 'Community', 'Care Types', 'Score'], result.after.accepted.slice(0, 10).map((item, index) => [index + 1, item.facility.name, item.facility.careTypes.join(', '), item.totalScore.toFixed(2)])));
    sections.push('');
    sections.push('### Care Type Distribution');
    sections.push('');
    sections.push(markdownTable(['Care Type', 'Top 10 Share', 'Count'], result.distribution));
    sections.push('');
    sections.push('### Dynamic Weight Table');
    sections.push('');
    sections.push(markdownTable(['Dimension', 'Weight'], result.weights.map((item) => [item.label, `${Math.round(item.weight * 100)}%`])));
    sections.push('');
    sections.push('### Top Positive Contributors');
    sections.push('');
    sections.push(contributorText(result.positiveContributors));
    sections.push('');
    sections.push('### Top Negative Contributors');
    sections.push('');
    sections.push(contributorText(result.negativeContributors));
    sections.push('');
    sections.push('### Before vs After');
    sections.push('');
    sections.push(markdownTable(['Community', 'Before Rank', 'After Rank', 'Rank Change', 'After Care Types'], result.beforeAfter));
    sections.push('');
    sections.push(`Persona Verdict: **${verdict.passed ? 'PASS' : 'FAIL'}**`);
    if (verdict.failures.length > 0) {
      verdict.failures.forEach((failure) => sections.push(`- ${failure}`));
    }
    sections.push('');
  });

  return sections.join('\n');
}

function main() {
  const backendFacilities = loadBackendFacilities();
  const legacyFacilities = backendFacilities.map((facility) => toSearchFacility(facility, 'legacy'));
  const migratedFacilities = backendFacilities.map((facility) => toSearchFacility(facility, 'post'));
  const results = Object.entries(personaStates()).map(([code, state]) => analyzePersona(code, state, legacyFacilities, migratedFacilities));
  const markdown = buildReport(results);
  const csv = buildCsv(results);
  const markdownPath = path.join(repoRoot, 'reports', 'post_taxonomy_validation_report.md');
  const csvPath = path.join(repoRoot, 'reports', 'post_taxonomy_validation_report.csv');
  fs.writeFileSync(markdownPath, markdown);
  fs.writeFileSync(csvPath, csv);
  console.log(`Wrote ${markdownPath}`);
  console.log(`Wrote ${csvPath}`);
  console.log(markdown);
}

main();
