# Adaptive Interview Current Code Extract

Current local-worktree evidence. All line ranges are 1-based and refer to the files as inspected when this report was generated.

## Active entry point

**Path:** `frontend/src/app/assessment/page.tsx`  
**Lines:** 1-5  
**Symbol:** `AssessmentPage`

```tsx
import { AssessmentAdvisorExperience } from "@/components/assessment/assessment-advisor-experience";

export default function AssessmentPage() {
  return <AssessmentAdvisorExperience />;
}
```

The same experience is the home-page entry point.

**Path:** `frontend/src/app/page.tsx`  
**Lines:** 1-5  
**Symbol:** `Home`

```tsx
import { AssessmentAdvisorExperience } from "@/components/assessment/assessment-advisor-experience";

export default function Home() {
  return <AssessmentAdvisorExperience />;
}
```

## 1. Next-question selection

### Answer/relevance predicates

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 125-137  
**Symbols:** `hasAnswer`, `isUnknown`, `isAdvisorQuestionRelevant`

```ts
function hasAnswer(answer: AssessmentAnswer | undefined): boolean {
  if (Array.isArray(answer)) return answer.length > 0;
  if (typeof answer === "number") return Number.isFinite(answer);
  return typeof answer === "string" && answer.trim().length > 0;
}

function isUnknown(answer: AssessmentAnswer | undefined): boolean {
  return answer === UNKNOWN_FROM_FAMILY || (Array.isArray(answer) && answer.includes(UNKNOWN_FROM_FAMILY));
}

export function isAdvisorQuestionRelevant(question: AssessmentQuestion): boolean {
  return ["who_needs_care", "avoid_search_areas"].includes(question.id) || question.rankingRelevant || question.eligibilityRelevant;
}
```

### Base priority, adaptive context bonus, governed parameter influence, and total score

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 74-97  
**Symbol:** `BASE_IMPACT`

```ts
const BASE_IMPACT: Record<string, number> = {
  who_needs_care: 10000,
  preferred_search_area: 9000,
  avoid_search_areas: 8900,
  urgency: 9300,
  rehabilitation_needed: 8600,
  mobility: 8500,
  cognitive_status: 8400,
  nursing_needs: 8300,
  daily_activities: 8200,
  medication_support: 8100,
  payment_method: 8000,
  distance_from_family: 7800,
  transfer_assistance: 7700,
  family_priorities: 7500,
  dietary_requirements: 6400,
  language_needs: 6300,
  room_preference: 6200,
  culture_importance: 6000,
  current_living_situation: 5000,
  social_activity_preferences: 4200,
  deal_breakers: 4000,
  continue_method: 100,
};
```

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 158-196  
**Symbols:** `contextBonus`, `parameterRecordsFor`, `parameterInfluence`, `questionScore`

```ts
function contextBonus(question: AssessmentQuestion, answers: AssessmentAnswers): number {
  const preferredAreasSelected = Array.isArray(answers.preferred_search_area) ? answers.preferred_search_area.length > 0 : typeof answers.preferred_search_area === "string" && answers.preferred_search_area.trim().length > 0;
  if (question.id === "avoid_search_areas" && preferredAreasSelected) return 14600;
  if (question.id === "urgency" && preferredAreasSelected) return 14300;
  if (question.id === "urgent_availability" && ["IMMEDIATE", "WITHIN_30_DAYS"].includes(String(answers.urgency))) return 14500;
  if (question.id === "rehabilitation_focus" && answers.rehabilitation_needed === "YES") return 14200;
  if (question.id === "stroke_recovery" && Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("STROKE")) return 15000;
  if (question.id === "neurological_rehabilitation" && Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("NEUROLOGICAL")) return 14900;
  if (question.id === "rehabilitation_services" && answers.rehabilitation_needed === "YES") return 13500;
  if (question.id === "gluten_free_details" && Array.isArray(answers.dietary_requirements) && answers.dietary_requirements.includes("GLUTEN_FREE")) return 14000;
  if (question.id === "hebrew_support" && Array.isArray(answers.language_needs) && answers.language_needs.includes("HEBREW")) return 14000;
  if (question.id === "monthly_budget" && Array.isArray(answers.payment_method) && answers.payment_method.includes("PRIVATE_PAY")) return 14000;
  if (question.id === "cultural_preferences" && ["SOMEWHAT", "IMPORTANT", "VERY_IMPORTANT"].includes(String(answers.culture_importance))) return 12500;
  return 0;
}

function parameterRecordsFor(question: AssessmentQuestion): ParameterIntelligenceRecord[] {
  const parameterIds = question.canonicalMappings.flatMap((mapping) => {
    if (mapping.startsWith("parameters.")) return [mapping.slice("parameters.".length)];
    return CANONICAL_MAPPING_ALIASES[mapping] || [];
  });
  return Array.from(new Set(parameterIds)).map((parameterId) => PARAMETER_BY_ID.get(parameterId)).filter((record): record is ParameterIntelligenceRecord => Boolean(record));
}

function parameterInfluence(question: AssessmentQuestion): number {
  return parameterRecordsFor(question).reduce((score, record) => score
    + (record.hard_filter_eligibility ? 120 : 0)
    + (record.ranking_eligibility ? 60 : 0)
    + (record.requires_facility_confirmation ? 50 : 0)
    + (record.dynamic ? 70 : 0)
    + (record.criticality === "CRITICAL" ? 50 : 0)
    + (record.ranking_eligibility || record.hard_filter_eligibility ? Math.min(80, Math.round(Number(record.current_coverage_percent || 0) * 0.8)) : 0), 0);
}

function questionScore(question: AssessmentQuestion, answers: AssessmentAnswers): number {
  const governedImpact = (question.eligibilityRelevant ? 500 : 0) + (question.rankingRelevant ? 250 : 0) + (question.required ? 50 : 0);
  const canonicalDepth = Math.min(150, question.canonicalMappings.length * 50);
  return Math.max(BASE_IMPACT[question.id] || 3000, contextBonus(question, answers)) + governedImpact + canonicalDepth + parameterInfluence(question);
}
```

### Candidate filtering, scoring, deterministic tie-break, and selected turn

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 334-360  
**Symbol:** `selectAdvisorTurn`

```ts
export function selectAdvisorTurn(answers: AssessmentAnswers): AdvisorTurn | null {
  const candidates = getVisibleQuestions(answers).filter((question) => isAdvisorQuestionRelevant(question) && !hasAnswer(answers[question.id]));
  const selected = candidates
    .map((question, schemaIndex) => ({ question, schemaIndex, score: questionScore(question, answers) }))
    .sort((left, right) => right.score - left.score || left.schemaIndex - right.schemaIndex)[0];
  if (!selected) return null;

  const factors = [
    selected.question.eligibilityRelevant ? "can change eligibility" : "refines the resident profile",
    selected.question.rankingRelevant ? "can change recommendation order" : "improves interpretation",
    contextBonus(selected.question, answers) ? "activated by a previous answer" : "high-value unresolved domain",
    `${selected.question.canonicalMappings.length} canonical mapping${selected.question.canonicalMappings.length === 1 ? "" : "s"}`,
    `${parameterRecordsFor(selected.question).length} governed facility parameter definition${parameterRecordsFor(selected.question).length === 1 ? "" : "s"}`,
  ];

  return {
    question: selected.question,
    prompt: buildAdvisorPrompt(selected.question, answers),
    rationale: rationaleFor(selected.question, answers),
    knownFacts: knownFacts(answers),
    uncertainties: uncertainties(selected.question, answers),
    knowledgeSources: knowledgeSourcesFor(selected.question),
    informationGainScore: Math.min(100, Math.round(selected.score / 160)),
    decisionFactors: factors,
    canonicalParameters: canonicalParametersFor(selected.question),
  };
}
```

### Re-selection after an answer is committed

**Path:** `frontend/src/components/assessment/conversational-assessment.tsx`  
**Lines:** 29-54  
**Symbols:** `ConversationalAssessment`, `commitAnswer`

```tsx
  const activeTurn = useRef<HTMLElement | null>(null);
  const visibleQuestions = useMemo(() => getConversationQuestions(answers), [answers]);
  const selectedAdvisorTurn = useMemo(() => selectAdvisorTurn(answers), [answers]);
  const advisorTurn = settlingTurn || selectedAdvisorTurn;
  const visibleQuestionById = useMemo(() => new Map(visibleQuestions.map((question) => [question.id, question])), [visibleQuestions]);
  const answeredQuestions = Object.keys(answers)
    .map((questionId) => visibleQuestionById.get(questionId))
    .filter((question): question is AssessmentQuestion => Boolean(question && question.id !== settlingTurn?.question.id && hasAssessmentAnswer(answers[question.id])));
  const nextQuestion = advisorTurn?.question;
  const nextQuestionId = nextQuestion?.id;
  const complete = isAdvisorReadyForMatch(answers);
  const completionSummary = useMemo(() => buildAdvisorCompletionSummary(answers), [answers]);

  useEffect(() => {
    if (!nextQuestionId || !activeTurn.current) return;
    activeTurn.current.scrollIntoView({ behavior: "auto", block: "center" });
  }, [nextQuestionId]);

  const commitAnswer = (questionId: string, answer: AssessmentAnswer) => {
    const pruned = pruneHiddenAssessmentAnswers({ ...answers, [questionId]: answer });
    const nextCurrent = selectAdvisorTurn(pruned.answers)?.question;
    onAnswersChange(pruned.answers);
    setSettlingTurn(null);
    setEditingQuestionId(null);
    if (nextCurrent) onCurrentQuestionChange(nextCurrent.id);
    setClearedNotice(pruned.clearedQuestionIds.length ? "I removed a detail that no longer applies after this update." : "");
  };
```

## 2. Question eligibility and dependencies

### Question contract

**Path:** `frontend/src/lib/assessment-schema.ts`  
**Lines:** 19-47  
**Symbols:** `DisplayRule`, `AssessmentQuestion`

```ts
export type AssessmentAnswerType = "single" | "multi" | "text" | "number" | "priority";

export type AssessmentOption = {
  value: string;
  label: string;
  hebrewLabel: string;
  description?: string;
};

export type DisplayRule = {
  questionId: string;
  operator: "answered" | "equals" | "includes" | "one_of";
  value: string | string[];
};

export type AssessmentQuestion = {
  id: string;
  version: typeof ASSESSMENT_SCHEMA_VERSION;
  category: string;
  decisionArea: DecisionArea;
  canonicalMappings: string[];
  englishLabel: string;
  hebrewLabel: string;
  answerType: AssessmentAnswerType;
  options?: AssessmentOption[];
  required: boolean;
  showIf?: DisplayRule;
  helpText: string;
  rankingRelevant: boolean;
  eligibilityRelevant: boolean;
  placeholder?: string;
  maxSelections?: number;
};
```

### Dependency declarations currently present in the schema

**Path:** `frontend/src/lib/assessment-schema.ts`  
**Lines:** 62, 64, 73-77, 79, 81, 83, 87  
**Symbol:** `ASSESSMENT_QUESTIONS` (`showIf` fields)

```ts
  question({ id: "avoid_search_areas", category: "Location", decisionArea: "avoid_search_areas", canonicalMappings: ["logistics.location.preferred"], englishLabel: "Are there any areas you'd rather avoid?", hebrewLabel: "האם יש אזורים שעדיף להימנע מהם?", answerType: "multi", required: true, helpText: "Select everything that applies.", rankingRelevant: false, eligibilityRelevant: false, showIf: { questionId: "preferred_search_area", operator: "answered", value: "" }, options: [...regionAreas.filter((area) => area.value !== ACTIVE_ASSESSMENT_REGION.allAreasValue), option("NONE", "No areas to avoid", "אין אזורים להימנע מהם"), uncertainty] }),
  question({ id: "urgent_availability", category: "Timing", decisionArea: "urgency", canonicalMappings: ["recommendation_constraints.immediate_availability"], englishLabel: "Is immediate bed availability a deal-breaker?", hebrewLabel: "האם זמינות מיטה מיידית היא תנאי הכרחי?", answerType: "single", required: true, helpText: "Availability changes often and must still be verified with each facility.", rankingRelevant: true, eligibilityRelevant: false, showIf: { questionId: "urgency", operator: "one_of", value: ["IMMEDIATE", "WITHIN_30_DAYS"] }, options: yesNoUnknown }),
  question({ id: "rehabilitation_focus", category: "Rehabilitation", decisionArea: "rehabilitation_needs", canonicalMappings: ["clinical.rehabilitation_focus"], englishLabel: "What is the rehabilitation focus?", hebrewLabel: "מהו מוקד השיקום?", answerType: "multi", required: true, helpText: "Select everything that applies.", rankingRelevant: true, eligibilityRelevant: true, showIf: { questionId: "rehabilitation_needed", operator: "equals", value: "YES" }, options: [option("STROKE", "Stroke recovery", "שיקום לאחר שבץ"), option("NEUROLOGICAL", "Neurological condition", "מצב נוירולוגי"), option("ORTHOPEDIC", "Orthopedic recovery", "שיקום אורתופדי"), option("CARDIAC", "Cardiac recovery", "שיקום לבבי"), option("GENERAL", "General strengthening", "חיזוק כללי"), uncertainty] }),
  question({ id: "rehabilitation_services", category: "Rehabilitation", decisionArea: "rehabilitation_services", canonicalMappings: ["clinical.therapy.pt", "parameters.pt", "clinical.therapy.ot", "parameters.ot", "clinical.therapy.speech", "parameters.speech_therapy"], englishLabel: "Which rehabilitation services are part of the care plan?", hebrewLabel: "אילו שירותי שיקום הם חלק מתוכנית הטיפול?", answerType: "multi", required: true, helpText: "Select everything that applies.", rankingRelevant: true, eligibilityRelevant: true, showIf: { questionId: "rehabilitation_needed", operator: "equals", value: "YES" }, options: [option("PHYSICAL_THERAPY", "Physical therapy", "פיזיותרפיה"), option("OCCUPATIONAL_THERAPY", "Occupational therapy", "ריפוי בעיסוק"), option("SPEECH_THERAPY", "Speech or swallowing therapy", "טיפול בדיבור או בבליעה"), option("NONE", "No specific therapy selected", "לא נבחר טיפול מסוים"), uncertainty] }),
  question({ id: "therapy_frequency", category: "Rehabilitation", decisionArea: "rehabilitation_needs", canonicalMappings: ["clinical.therapy.frequency"], englishLabel: "Is a preferred therapy frequency known?", hebrewLabel: "האם ידועה תדירות טיפול מועדפת?", answerType: "single", required: false, helpText: "A preference is not a guarantee; the clinical team determines the treatment plan.", rankingRelevant: false, eligibilityRelevant: false, showIf: { questionId: "rehabilitation_needed", operator: "equals", value: "YES" }, options: [option("DAILY", "Daily if clinically appropriate", "יומי אם מתאים מבחינה קלינית"), option("FIVE_DAYS", "About five days per week", "כחמישה ימים בשבוע"), option("THREE_DAYS", "About three days per week", "כשלושה ימים בשבוע"), option("CLINICAL_PLAN", "Follow the clinical plan", "לפי התוכנית הקלינית"), uncertainty] }),
  question({ id: "stroke_recovery", category: "Rehabilitation", decisionArea: "stroke_recovery", canonicalMappings: ["clinical.stroke_recovery", "parameters.post_stroke_neuro_evidence"], englishLabel: "Does stroke recovery require a dedicated program?", hebrewLabel: "האם שיקום לאחר שבץ דורש תוכנית ייעודית?", answerType: "single", required: true, helpText: "This helps distinguish a structured stroke program from general rehabilitation.", rankingRelevant: true, eligibilityRelevant: true, showIf: { questionId: "rehabilitation_focus", operator: "includes", value: "STROKE" }, options: yesNoUnknown }),
  question({ id: "neurological_rehabilitation", category: "Rehabilitation", decisionArea: "neurological_rehabilitation", canonicalMappings: ["clinical.neurological_rehabilitation", "parameters.post_stroke_neuro_evidence"], englishLabel: "Is a neurological rehabilitation program required?", hebrewLabel: "האם נדרשת תוכנית שיקום נוירולוגי?", answerType: "single", required: true, helpText: "This is separate from a general rehabilitation claim.", rankingRelevant: true, eligibilityRelevant: true, showIf: { questionId: "rehabilitation_focus", operator: "includes", value: "NEUROLOGICAL" }, options: yesNoUnknown }),
  question({ id: "gluten_free_details", category: "Food and diet", decisionArea: "dietary_requirements", canonicalMappings: ["culture.diet.gluten_free_safety", "parameters.gluten_free"], englishLabel: "How strict must gluten-free preparation be?", hebrewLabel: "עד כמה ההכנה ללא גלוטן חייבת להיות קפדנית?", answerType: "single", required: true, helpText: "This distinguishes preference from medically necessary cross-contamination controls.", rankingRelevant: true, eligibilityRelevant: false, showIf: { questionId: "dietary_requirements", operator: "includes", value: "GLUTEN_FREE" }, options: [option("PREFERENCE", "Preference", "העדפה"), option("MEDICALLY_REQUIRED", "Medically required", "נדרש רפואית"), option("CROSS_CONTAMINATION", "Strict cross-contamination controls required", "נדרשת מניעת זיהום צולב קפדנית"), uncertainty] }),
  question({ id: "hebrew_support", category: "Language and culture", decisionArea: "language_needs", canonicalMappings: ["communication.hebrew_support", "parameters.languages"], englishLabel: "Where is Hebrew support most important?", hebrewLabel: "באילו מצבים התמיכה בעברית חשובה ביותר?", answerType: "multi", required: true, helpText: "Select everything that applies.", rankingRelevant: true, eligibilityRelevant: false, showIf: { questionId: "language_needs", operator: "includes", value: "HEBREW" }, options: [option("DAILY", "Daily conversation", "שיחה יומיומית"), option("MEDICAL", "Medical discussions", "שיחות רפואיות"), option("ACTIVITIES", "Activities and community", "פעילויות וקהילה"), option("FAMILY", "Family communication", "תקשורת עם המשפחה"), uncertainty] }),
  question({ id: "cultural_preferences", category: "Language and culture", decisionArea: "religious_cultural_preferences", canonicalMappings: ["culture.religion", "preferences.cultural"], englishLabel: "Which cultural or religious supports matter?", hebrewLabel: "אילו תמיכות תרבותיות או דתיות חשובות?", answerType: "multi", required: true, helpText: "Select everything that applies.", rankingRelevant: true, eligibilityRelevant: false, showIf: { questionId: "culture_importance", operator: "one_of", value: ["SOMEWHAT", "IMPORTANT", "VERY_IMPORTANT"] }, options: [option("JEWISH", "Jewish community or programming", "קהילה או תוכן יהודי"), option("CHRISTIAN", "Christian services", "שירותים נוצריים"), option("MUSLIM", "Muslim community or prayer support", "קהילה מוסלמית או תמיכה בתפילה"), option("WORSHIP", "Access to worship", "גישה לתפילה"), option("HOLIDAYS", "Holiday observance", "ציון חגים"), option("OTHER", "Another tradition", "מסורת אחרת"), uncertainty] }),
  question({ id: "monthly_budget", category: "Budget and coverage", decisionArea: "budget", canonicalMappings: ["financial.budget", "parameters.published_rates"], englishLabel: "What monthly private-pay range feels manageable?", hebrewLabel: "איזה תקציב חודשי פרטי מרגיש אפשרי?", answerType: "single", required: true, helpText: "This is a planning range, not a price quote.", rankingRelevant: true, eligibilityRelevant: true, showIf: { questionId: "payment_method", operator: "includes", value: "PRIVATE_PAY" }, options: [option("UNDER_5000", "Under $5,000", "פחות מ-5,000 דולר"), option("5000_7500", "$5,000 to $7,500", "5,000 עד 7,500 דולר"), option("7500_10000", "$7,500 to $10,000", "7,500 עד 10,000 דולר"), option("10000_15000", "$10,000 to $15,000", "10,000 עד 15,000 דולר"), option("OVER_15000", "Over $15,000", "מעל 15,000 דולר"), uncertainty] }),
```

### Dependency evaluation

**Path:** `frontend/src/lib/assessment-schema.ts`  
**Lines:** 94-105  
**Symbols:** `isQuestionVisible`, `getVisibleQuestions`

```ts
export function isQuestionVisible(question: AssessmentQuestion, answers: AssessmentAnswers): boolean {
  if (!question.showIf) return true;
  const actual = answers[question.showIf.questionId];
  if (question.showIf.operator === "answered") return Array.isArray(actual) ? actual.length > 0 : actual !== undefined && String(actual).trim().length > 0;
  if (question.showIf.operator === "equals") return actual === question.showIf.value;
  if (question.showIf.operator === "includes") return Array.isArray(actual) && actual.includes(String(question.showIf.value));
  return Array.isArray(question.showIf.value) && question.showIf.value.includes(String(actual));
}

export function getVisibleQuestions(answers: AssessmentAnswers): AssessmentQuestion[] {
  return ASSESSMENT_QUESTIONS.filter((questionItem) => isQuestionVisible(questionItem, answers));
}
```

### Removal of answers whose dependencies become false

**Path:** `frontend/src/lib/assessment-conversation.ts`  
**Lines:** 69-86  
**Symbol:** `pruneHiddenAssessmentAnswers`

```ts
export function pruneHiddenAssessmentAnswers(answers: AssessmentAnswers): { answers: AssessmentAnswers; clearedQuestionIds: string[] } {
  const next = { ...answers };
  const clearedQuestionIds: string[] = [];
  let changed = true;

  while (changed) {
    changed = false;
    const visibleIds = new Set(getVisibleQuestions(next).map((question) => question.id));
    for (const question of ASSESSMENT_QUESTIONS) {
      if (!visibleIds.has(question.id) && question.id in next) {
        delete next[question.id];
        clearedQuestionIds.push(question.id);
        changed = true;
      }
    }
  }

  return { answers: next, clearedQuestionIds };
}
```

## 3. Decision-area completion

### Decision-area inventory

**Path:** `frontend/src/lib/assessment-schema.ts`  
**Lines:** 6-15  
**Symbols:** `DECISION_AREAS`, `DecisionArea`

```ts
export const DECISION_AREAS = [
  "who_needs_care", "preferred_search_area", "avoid_search_areas", "urgency", "current_living_situation",
  "mobility", "daily_activities", "transfer_assistance", "medication_support", "cognitive_status",
  "nursing_needs", "rehabilitation_needs", "rehabilitation_services",
  "stroke_recovery", "neurological_rehabilitation", "dietary_requirements", "language_needs",
  "religious_cultural_preferences", "social_activity_preferences", "room_preference", "budget",
  "payment_method", "distance_from_family", "family_priorities", "deal_breakers", "contact_details",
] as const;

export type DecisionArea = (typeof DECISION_AREAS)[number];
```

### Stage grouping and decision-area completion calculation

**Path:** `frontend/src/lib/assessment-home-progress.ts`  
**Lines:** 19-61  
**Symbols:** `HOME_PROGRESS_STAGES`, `getHomeProgress`

```ts
export const HOME_PROGRESS_STAGES: HomeProgressStage[] = [
  { id: "foundation", label: "Foundation", description: "Who needs care and the family situation", decisionAreas: ["who_needs_care", "current_living_situation"] },
  { id: "walls", label: "Support walls", description: "Mobility and daily living support", decisionAreas: ["mobility", "daily_activities"] },
  { id: "windows", label: "Care windows", description: "Medical, nursing, memory, and rehabilitation needs", decisionAreas: ["medication_support", "cognitive_status", "nursing_needs", "rehabilitation_needs", "rehabilitation_services", "stroke_recovery", "neurological_rehabilitation"] },
  { id: "roof-frame", label: "Roof structure", description: "Location, timing, and availability", decisionAreas: ["preferred_search_area", "avoid_search_areas", "urgency"] },
  { id: "roof", label: "Shelter", description: "Budget, payment, and room preferences", decisionAreas: ["budget", "payment_method", "room_preference"] },
  { id: "access", label: "Door and path", description: "Transfers and family access", decisionAreas: ["transfer_assistance", "distance_from_family"] },
  { id: "garden", label: "Garden", description: "Activities and everyday preferences", decisionAreas: ["social_activity_preferences"] },
  { id: "lights", label: "Warm lights", description: "Language, culture, and dietary needs", decisionAreas: ["language_needs", "religious_cultural_preferences", "dietary_requirements"] },
  { id: "complete", label: "Ready home", description: "Priorities and deal-breakers resolved", decisionAreas: ["family_priorities", "deal_breakers"] },
];

export function getHomeProgress(answers: AssessmentAnswers): { stages: HomeProgressStageState[]; completedDecisionAreas: DecisionArea[]; currentStageId: string; ready: boolean } {
  const relevantVisibleQuestions = getVisibleQuestions(answers).filter(isAdvisorQuestionRelevant);
  const availableAreas = new Set(relevantVisibleQuestions.map((question) => question.decisionArea));
  const completedAreas = new Set(
    relevantVisibleQuestions
      .filter((question) => hasAssessmentAnswer(answers[question.id]))
      .map((question) => question.decisionArea),
  );
  const ready = isAdvisorReadyForMatch(answers);

  const stages = HOME_PROGRESS_STAGES.map((stage) => {
    const stageAreas = stage.decisionAreas.filter((area) => availableAreas.has(area));
    const completedStageAreas = stageAreas.filter((area) => completedAreas.has(area));
    const complete = stage.id === "complete"
      ? ready
      : stageAreas.length > 0 && completedStageAreas.length === stageAreas.length;
    return {
      ...stage,
      completedAreas: completedStageAreas.length,
      availableAreas: stageAreas.length,
      revealed: complete || completedStageAreas.length > 0,
      complete,
    };
  });

  const questionById = new Map(relevantVisibleQuestions.map((question) => [question.id, question]));
  const latestArea = Object.keys(answers).reverse().map((questionId) => questionById.get(questionId)?.decisionArea).find((area): area is DecisionArea => Boolean(area));
  const currentStageId = ready ? "complete" : HOME_PROGRESS_STAGES.find((stage) => latestArea && stage.decisionAreas.includes(latestArea))?.id || "foundation";

  return { stages, completedDecisionAreas: Array.from(completedAreas), currentStageId, ready };
}
```

## 4. Assessment progress/readiness calculation

### Readiness gate used by the active interview

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 362-364  
**Symbol:** `isAdvisorReadyForMatch`

```ts
export function isAdvisorReadyForMatch(answers: AssessmentAnswers): boolean {
  return Object.keys(answers).length > 0 && selectAdvisorTurn(answers) === null;
}
```

### Stage counts and readiness

The active decision-area progress calculation is the complete `getHomeProgress` function in Section 3, lines 31-61 of `frontend/src/lib/assessment-home-progress.ts`. The visual environment converts those counts into a bounded reveal ratio as follows.

**Path:** `frontend/src/components/assessment/assessment-photo-environment.tsx`  
**Lines:** 74-83  
**Symbol:** `AssessmentPhotoEnvironment` (`reveal` calculation)

```tsx
  const reveal = useMemo(() => {
    const completed = progress.stages.reduce((sum, stage) => sum + stage.completedAreas, 0);
    const available = progress.stages.reduce((sum, stage) => sum + stage.availableAreas, 0);
    return progress.ready ? 1 : Math.min(0.9, available > 0 ? completed / available : 0);
  }, [progress]);
  const blur = Math.round((1 - reveal) * 14);
  const brightness = 0.62 + reveal * 0.28;
  const saturation = 0.48 + reveal * 0.48;
  const warmth = Math.round(reveal * 9);
```

## 5. Interview completion condition

### Terminal condition

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 334-364  
**Symbols:** `selectAdvisorTurn`, `isAdvisorReadyForMatch`

```ts
export function selectAdvisorTurn(answers: AssessmentAnswers): AdvisorTurn | null {
  const candidates = getVisibleQuestions(answers).filter((question) => isAdvisorQuestionRelevant(question) && !hasAnswer(answers[question.id]));
  const selected = candidates
    .map((question, schemaIndex) => ({ question, schemaIndex, score: questionScore(question, answers) }))
    .sort((left, right) => right.score - left.score || left.schemaIndex - right.schemaIndex)[0];
  if (!selected) return null;

  const factors = [
    selected.question.eligibilityRelevant ? "can change eligibility" : "refines the resident profile",
    selected.question.rankingRelevant ? "can change recommendation order" : "improves interpretation",
    contextBonus(selected.question, answers) ? "activated by a previous answer" : "high-value unresolved domain",
    `${selected.question.canonicalMappings.length} canonical mapping${selected.question.canonicalMappings.length === 1 ? "" : "s"}`,
    `${parameterRecordsFor(selected.question).length} governed facility parameter definition${parameterRecordsFor(selected.question).length === 1 ? "" : "s"}`,
  ];

  return {
    question: selected.question,
    prompt: buildAdvisorPrompt(selected.question, answers),
    rationale: rationaleFor(selected.question, answers),
    knownFacts: knownFacts(answers),
    uncertainties: uncertainties(selected.question, answers),
    knowledgeSources: knowledgeSourcesFor(selected.question),
    informationGainScore: Math.min(100, Math.round(selected.score / 160)),
    decisionFactors: factors,
    canonicalParameters: canonicalParametersFor(selected.question),
  };
}

export function isAdvisorReadyForMatch(answers: AssessmentAnswers): boolean {
  return Object.keys(answers).length > 0 && selectAdvisorTurn(answers) === null;
}
```

### Completion UI gate

**Path:** `frontend/src/components/assessment/conversational-assessment.tsx`  
**Lines:** 98-114  
**Symbol:** `ConversationalAssessment`

```tsx
      {complete ? (
        <section className="border-t-2 border-[#2f4d43] pt-10" aria-labelledby="document-summary-heading">
          <AdvisorWritingBlock
            label="readiness"
            lines={[{
              text: "I now understand enough about your family's needs to begin finding the communities most likely to fit.",
              id: "document-summary-heading",
              as: "h2",
              className: "max-w-3xl font-serif text-3xl leading-tight text-[#292722] sm:text-5xl",
            }]}
          />
          {completionSummary.stillNeedsConfirmation.length ? <p className="mt-5 max-w-3xl text-lg leading-8 text-[#625d55]">A few answers remain uncertain, and I will preserve them as unknown while I compare the options.</p> : null}

          <ValidationMessage message={validation} />
          <MatchReadinessAction ready={complete} submitting={submitting} recommendationsReady={recommendationsReady} onActivate={activateMatch} />
        </section>
      ) : <ValidationMessage message={validation} />}
```

## 6. Transition to recommendations

### Completion action

**Path:** `frontend/src/components/assessment/conversational-assessment.tsx`  
**Lines:** 68-75  
**Symbol:** `activateMatch`

```tsx
  const activateMatch = () => {
    if (recommendationsReady) {
      document.getElementById("recommendations-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    void onSubmit();
  };
```

**Path:** `frontend/src/components/assessment/match-readiness-action.tsx`  
**Lines:** 1-20  
**Symbol:** `MatchReadinessAction`

```tsx
export function MatchReadinessAction({ ready, submitting, recommendationsReady, onActivate }: {
  ready: boolean;
  submitting: boolean;
  recommendationsReady: boolean;
  onActivate: () => void;
}) {
  if (!ready) return null;

  return (
    <div data-match-readiness-action className="mt-8">
      <button
        type="button"
        disabled={submitting}
        onClick={onActivate}
        className="mt-4 min-h-12 border-b-2 border-[#2f6f5e] pb-1 text-left text-lg font-semibold text-[#2f6f5e] transition hover:border-[#1f4f42] hover:text-[#1f4f42] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#2f6f5e] disabled:cursor-wait disabled:opacity-60"
      >
        {submitting ? "Comparing communities" : recommendationsReady ? "View the matches below" : "Find My Best Matches"}
      </button>
    </div>
  );
}
```

### Patient-case conversion and recommendation request

**Path:** `frontend/src/components/assessment/assessment-advisor-experience.tsx`  
**Lines:** 57-80  
**Symbol:** `submit`

```tsx
  const submit = async () => {
    setSubmitting(true);
    setValidation("");
    try {
      const conversion = convertAssessmentToQuestionnaireState(draft.answers, state);
      setState(conversion.questionnaireState);
      const patientCase = await upsertPatientCaseFromQuestionnaire({
        patient_case_id: loadPatientCaseId() || undefined,
        questionnaire_state: conversion.questionnaireState as unknown as Record<string, unknown>,
        source_name: ASSESSMENT_SCHEMA_VERSION,
        reason: "family_assessment_submission",
      });
      savePatientCaseId(patientCase.id);
      const recommendations = await fetchPatientDecisionRecommendations({
        patient_case_id: patientCase.id,
        questionnaire_state: conversion.questionnaireState as unknown as Record<string, unknown>,
        natural_language_query: conversion.naturalLanguageQuery,
        limit: 50,
      });
      setDecisionResponse(recommendations);
    } catch (error) {
      setValidation(error instanceof Error ? error.message : "We could not create recommendations. Your answers remain saved on this device.");
    } finally {
      setSubmitting(false);
    }
  };
```

### Submit wiring and inline recommendation rendering

**Path:** `frontend/src/components/assessment/assessment-advisor-experience.tsx`  
**Lines:** 98-118  
**Symbol:** `AssessmentAdvisorExperience`

```tsx
      {hydrated ? (
        <ConversationalAssessment
          answers={draft.answers}
          validation={validation}
          submitting={submitting}
          recommendationsReady={Boolean(decisionResponse)}
          onAnswersChange={(answers) => {
            updateAnswers(answers);
            setValidation("");
          }}
          onCurrentQuestionChange={updateCurrentQuestion}
          onSubmit={submit}
        />
      ) : <p className="py-12 text-lg text-[#405d53]" role="status">Restoring our conversation...</p>}
      {submitting || decisionResponse ? <ComparisonNarrative /> : null}
      {decisionResponse ? <LivingRecommendationDocument response={decisionResponse} personLabel={personLabel(draft.answers.who_needs_care)} /> : null}
    </QuestionnaireShell>
```

## 7. Confidence, sufficiency, readiness, and information gain

### Information-gain output field

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 27-38  
**Symbol:** `AdvisorTurn`

```ts
export type AdvisorTurn = {
  question: AssessmentQuestion;
  prompt: string;
  rationale: string;
  knownFacts: string[];
  uncertainties: string[];
  knowledgeSources: AdvisorKnowledgeSource[];
  informationGainScore: number;
  decisionFactors: string[];
  canonicalParameters: AdvisorCanonicalParameter[];
};
```

### Information-gain calculation

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 192-196 and 348-359  
**Symbols:** `questionScore`, `selectAdvisorTurn`

```ts
function questionScore(question: AssessmentQuestion, answers: AssessmentAnswers): number {
  const governedImpact = (question.eligibilityRelevant ? 500 : 0) + (question.rankingRelevant ? 250 : 0) + (question.required ? 50 : 0);
  const canonicalDepth = Math.min(150, question.canonicalMappings.length * 50);
  return Math.max(BASE_IMPACT[question.id] || 3000, contextBonus(question, answers)) + governedImpact + canonicalDepth + parameterInfluence(question);
}
```

```ts
  return {
    question: selected.question,
    prompt: buildAdvisorPrompt(selected.question, answers),
    rationale: rationaleFor(selected.question, answers),
    knownFacts: knownFacts(answers),
    uncertainties: uncertainties(selected.question, answers),
    knowledgeSources: knowledgeSourcesFor(selected.question),
    informationGainScore: Math.min(100, Math.round(selected.score / 160)),
    decisionFactors: factors,
    canonicalParameters: canonicalParametersFor(selected.question),
  };
```

### Completion confidence and remaining confirmation calculation

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 366-384  
**Symbol:** `buildAdvisorCompletionSummary`

```ts
export function buildAdvisorCompletionSummary(answers: AssessmentAnswers): AdvisorCompletionSummary {
  const relevantQuestions = getVisibleQuestions(answers).filter(isAdvisorQuestionRelevant);
  const unknownQuestions = relevantQuestions.filter((question) => isUnknown(answers[question.id]));
  const knownCount = relevantQuestions.filter((question) => hasAnswer(answers[question.id]) && !isUnknown(answers[question.id])).length;
  const knownRatio = relevantQuestions.length ? knownCount / relevantQuestions.length : 0;
  const confidence: AdvisorCompletionSummary["confidence"] = unknownQuestions.length === 0 && knownRatio >= 0.9 ? "Strong" : knownRatio >= 0.65 ? "Developing" : "Limited";

  const automaticVerification = relevantQuestions
    .filter((question) => hasAnswer(answers[question.id]))
    .flatMap(canonicalParametersFor)
    .filter((parameter) => parameter.dynamic || parameter.requiresFacilityConfirmation || parameter.currentCoveragePercent < 100)
    .map((parameter) => parameter.displayName);

  return {
    confidence,
    stillNeedsConfirmation: unknownQuestions.map((question) => question.englishLabel.replace(/\?$/, "")),
    automaticVerification: Array.from(new Set(automaticVerification)).slice(0, 5),
  };
}
```

### Readiness calculation

**Path:** `frontend/src/lib/assessment-advisor.ts`  
**Lines:** 362-364  
**Symbol:** `isAdvisorReadyForMatch`

```ts
export function isAdvisorReadyForMatch(answers: AssessmentAnswers): boolean {
  return Object.keys(answers).length > 0 && selectAdvisorTurn(answers) === null;
}
```

### Visual progress calculation

**Path:** `frontend/src/components/assessment/assessment-photo-environment.tsx`  
**Lines:** 74-79  
**Symbol:** `AssessmentPhotoEnvironment` (`reveal` calculation)

```tsx
  const reveal = useMemo(() => {
    const completed = progress.stages.reduce((sum, stage) => sum + stage.completedAreas, 0);
    const available = progress.stages.reduce((sum, stage) => sum + stage.availableAreas, 0);
    return progress.ready ? 1 : Math.min(0.9, available > 0 ? completed / available : 0);
  }, [progress]);
```
