"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useQuestionnaire, type QuestionnaireState } from "@/context/questionnaire-context";
import { OomnikMark } from "@/components/brand/oomnik-mark";

const assistanceOptions = [
  "Fully independent",
  "Light assistance",
  "Help with bathing",
  "Help with dressing",
  "Help with toileting",
  "Help with medications",
  "Daytime supervision",
  "24/7 support required",
  "Skilled nursing care",
];

const medicalOptions = [
  "Dialysis",
  "Oxygen",
  "Wound care",
  "Injections or infusions",
  "Complex medication management",
  "Complex chronic condition",
  "Permanent medical equipment",
  "Nursing supervision",
];

const moveConcernOptions = [
  "Good food",
  "Privacy",
  "Independence",
  "Social life",
  "Existing friends",
  "A specific class or activity",
  "Ability to go out independently",
  "Proximity to family",
  "My language or culture",
  "Daily routine",
  "Space for visitors",
  "A pet",
  "Transportation",
  "Other",
];

const activityOptions = ["Music", "Movies", "Games", "Exercise", "Outdoor activities", "Religious life", "Cultural activities", "Classes", "Volunteering"];
const dietaryOptions = ["Kosher", "Halal", "Vegetarian", "Vegan", "Low sodium", "Diabetic", "Gluten free", "Other"];

function toggle(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function Choice({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" aria-pressed={active} onClick={onClick} className={`rounded-full border px-4 py-2 text-left text-sm font-semibold transition ${active ? "border-[#397a69] bg-[#e8f4ef] text-[#245b4d]" : "border-[#ddd4c7] bg-white text-[#5e554b] hover:border-[#8eaa9f]"}`}>
      {active ? "✓ " : ""}{label}
    </button>
  );
}

function Choices({ options, value, onChange }: { options: string[]; value: string; onChange: (value: string) => void }) {
  return <div className="mt-3 flex flex-wrap gap-2">{options.map((option) => <Choice key={option} label={option} active={value === option} onClick={() => onChange(option)} />)}</div>;
}

function MultiChoices({ options, values, onChange }: { options: string[]; values: string[]; onChange: (values: string[]) => void }) {
  return <div className="mt-3 flex flex-wrap gap-2">{options.map((option) => <Choice key={option} label={option} active={values.includes(option)} onClick={() => onChange(toggle(values, option))} />)}</div>;
}

function Field({ label, value, onChange, placeholder = "" }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <label className="block text-sm font-semibold text-[#51483f]">{label}<input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="mt-2 w-full rounded-xl border border-[#ddd4c7] bg-white px-4 py-3 text-base font-normal outline-none focus:border-[#5a8c7d]" /></label>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-3xl border border-[#e2d9cc] bg-[#fffefb] p-6 shadow-sm"><h2 className="text-2xl font-semibold tracking-[-0.025em] text-[#25362f]">{title}</h2><div className="mt-5 space-y-5">{children}</div></section>;
}

export function StructuredIntake() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [draft, setDraft] = useState<QuestionnaireState>(() => JSON.parse(JSON.stringify(state)) as QuestionnaireState);
  const [assistance, setAssistance] = useState<string[]>(() => state.assistanceLevel ? state.assistanceLevel.split(", ") : []);
  const [activities, setActivities] = useState<string[]>(state.happinessPreferences || []);
  const [dietary, setDietary] = useState<string[]>(state.humanIntelligenceV2.foodProfile.dietaryPreferences || []);
  const [religiousCommunity, setReligiousCommunity] = useState(state.humanIntelligenceV2.culturalProfile.religionImportance === "Yes" ? "Yes" : state.humanIntelligenceV2.culturalProfile.religionImportance === "No" ? "No" : "");
  const [religion, setReligion] = useState(state.humanIntelligenceV2.culturalProfile.faithTraditions[0] || "");
  const [religiousNeeds, setReligiousNeeds] = useState(state.humanIntelligenceV2.culturalProfile.religiousSupportNeeds || []);
  const [socialFrequency, setSocialFrequency] = useState(state.humanIntelligenceV2.socialProfile.socialInteractionFrequency || "");
  const [communityStyle, setCommunityStyle] = useState(state.humanIntelligenceV2.personalityProfile.communitySizePreference || "");
  const [moveAttitude, setMoveAttitude] = useState(state.humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove || "");
  const [recentHospitalization, setRecentHospitalization] = useState(state.humanIntelligenceV2.transitionRiskProfile.recentHospitalization || "");
  const [rehabNeed, setRehabNeed] = useState(state.humanIntelligenceV2.transitionRiskProfile.postHospitalRehabNeed || "");
  const [hospitalTiming, setHospitalTiming] = useState(state.humanIntelligenceV2.transitionRiskProfile.hospitalizationRecency || "");
  const [memoryWandering, setMemoryWandering] = useState(state.humanIntelligenceV2.transitionRiskProfile.wanderingConcerns || "");
  const [secureMemory, setSecureMemory] = useState(state.humanIntelligenceV2.futureCareProfile.secureMemoryNeighborhoodNeed || "");
  const [language, setLanguage] = useState(state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage || "");
  const [medicalLanguage, setMedicalLanguage] = useState(state.humanIntelligenceV2.languageProfile.medicalDiscussionLanguage || "");
  const [continuum, setContinuum] = useState(state.humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference || "");
  const [confirmed, setConfirmed] = useState(false);
  const [showErrors, setShowErrors] = useState(false);

  const medical = draft.medicalCareProfile;
  const relationship = draft.relationship;
  const isCouple = relationship === "Couple";
  const needsMobilityFollowUp = assistance.some((item) => item !== "Fully independent");
  const hasMemoryConcern = Boolean(draft.memoryStatus && !["No", "Not sure"].includes(draft.memoryStatus));
  const needsMedicalDetails = medical.hasOngoingMedicalNeeds === "Yes";
  const needsDialysis = medical.needs.includes("Dialysis");
  const needsOxygen = medical.needs.includes("Oxygen");
  const needsWoundCare = medical.needs.includes("Wound care");
  const needsComplexDetails = medical.needs.some((item) => ["Complex chronic condition", "Complex medication management", "Injections or infusions", "Permanent medical equipment", "Nursing supervision"].includes(item));

  function update(patch: Partial<QuestionnaireState>) {
    setDraft((current) => ({ ...current, ...patch }));
    // Any answer change after checking "I confirm this summary reflects my
    // answers" means that confirmation no longer reflects what's on screen.
    setConfirmed(false);
  }

  function updateMedical(patch: Partial<QuestionnaireState["medicalCareProfile"]>) {
    setDraft((current) => ({ ...current, medicalCareProfile: { ...current.medicalCareProfile, ...patch } }));
    setConfirmed(false);
  }

  function updateAssistance(next: string[]) {
    setConfirmed(false);
    const added = next.find((item) => !assistance.includes(item));
    if (added === "Fully independent") {
      setAssistance(["Fully independent"]);
      return;
    }
    setAssistance(next.filter((item) => item !== "Fully independent"));
  }

  const missing = useMemo(() => {
    const rows: string[] = [];
    if (!draft.relationship) rows.push("who the search is for");
    if (!draft.ageGroup) rows.push("age group");
    if (assistance.length === 0) rows.push("daily assistance");
    if (!draft.memoryStatus) rows.push("memory status");
    if (needsMobilityFollowUp && (!medical.mobilityMethod || !medical.transferAssistance || !medical.recentFalls)) rows.push("mobility follow-up");
    if (hasMemoryConcern && (!memoryWandering || !secureMemory)) rows.push("memory safety follow-up");
    if (!medical.hasOngoingMedicalNeeds) rows.push("ongoing medical needs");
    if (needsMedicalDetails && medical.needs.length === 0) rows.push("medical need type");
    if (needsDialysis && (!medical.dialysisFrequency || !medical.dialysisTransportation)) rows.push("dialysis details");
    if (needsOxygen && !medical.oxygenUse) rows.push("oxygen details");
    if (needsWoundCare && !medical.woundCareFrequency) rows.push("wound-care details");
    if (needsComplexDetails && !medical.complexConditionDetails.trim()) rows.push("complex medical details");
    if (needsMedicalDetails && !medical.physicianCoordination) rows.push("medical coordination");
    if (!recentHospitalization) rows.push("recent hospitalization");
    if (recentHospitalization === "Yes" && (!hospitalTiming || !rehabNeed)) rows.push("hospitalization follow-up");
    if (rehabNeed === "Yes" && !draft.medicareStatus) rows.push("Medicare status");
    if (!draft.medicaidStatus) rows.push("Medicaid status");
    if (!draft.budget) rows.push("monthly budget");
    if (!socialFrequency || !communityStyle || activities.length === 0) rows.push("lifestyle preferences");
    if (draft.moveLossConcerns.length === 0) rows.push("move concerns");
    if (!language) rows.push("preferred language");
    if (language && language !== "English" && !medicalLanguage.trim()) rows.push("medical communication language");
    if (!religiousCommunity) rows.push("religious-community preference");
    if (religiousCommunity === "Yes" && (!religion || religiousNeeds.length === 0)) rows.push("religious follow-up");
    if (!draft.parkingRequirement) rows.push("parking requirement");
    if (isCouple && draft.parkingRequirement !== "No" && !draft.parkingVehicleCount) rows.push("number of parking spaces");
    if (!continuum) rows.push("future care continuity");
    if (!draft.locationImportant) rows.push("location importance");
    if (draft.locationImportant === "Yes" && (!draft.referenceAddress.trim() || !draft.maximumDistanceMiles)) rows.push("location details");
    if (!draft.moveTiming || !moveAttitude) rows.push("move timing and attitude");
    if (!confirmed) rows.push("confirmation of the summary");
    return rows;
  }, [activities.length, assistance, communityStyle, confirmed, continuum, draft, hasMemoryConcern, hospitalTiming, isCouple, language, medical, medicalLanguage, memoryWandering, moveAttitude, needsComplexDetails, needsDialysis, needsMedicalDetails, needsMobilityFollowUp, needsOxygen, needsWoundCare, recentHospitalization, rehabNeed, religion, religiousCommunity, religiousNeeds.length, secureMemory, socialFrequency]);

  function continueToInterview() {
    if (missing.length > 0) {
      setShowErrors(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const next: QuestionnaireState = {
      ...draft,
      assistanceLevel: assistance.join(", "),
      happinessPreferences: activities,
      medicareStatus: rehabNeed === "Yes" ? draft.medicareStatus : "",
      questionnaireCompletion: {
        mandatoryComplete: true,
        conditionalFollowUpsComplete: true,
        clientSummaryConfirmed: false,
        confirmedAt: "",
      },
      // Clear answers to follow-up questions whose parent answer no longer requires them, so a
      // reconsidered answer (e.g. medical needs Yes -> No, or assistance -> Fully independent)
      // can't leave stale, contradictory facts in the profile shown on the confirmation screen
      // and sent to the decision engine.
      medicalCareProfile: {
        ...draft.medicalCareProfile,
        mobilityMethod: needsMobilityFollowUp ? draft.medicalCareProfile.mobilityMethod : "",
        transferAssistance: needsMobilityFollowUp ? draft.medicalCareProfile.transferAssistance : "",
        recentFalls: needsMobilityFollowUp ? draft.medicalCareProfile.recentFalls : "",
        dialysisFrequency: needsDialysis ? draft.medicalCareProfile.dialysisFrequency : "",
        dialysisCenter: needsDialysis ? draft.medicalCareProfile.dialysisCenter : "",
        dialysisTransportation: needsDialysis ? draft.medicalCareProfile.dialysisTransportation : "",
        oxygenUse: needsOxygen ? draft.medicalCareProfile.oxygenUse : "",
        woundCareFrequency: needsWoundCare ? draft.medicalCareProfile.woundCareFrequency : "",
        complexConditionDetails: needsComplexDetails ? draft.medicalCareProfile.complexConditionDetails : "",
        physicianCoordination: needsMedicalDetails ? draft.medicalCareProfile.physicianCoordination : "",
      },
      humanIntelligenceV2: {
        ...draft.humanIntelligenceV2,
        socialProfile: { ...draft.humanIntelligenceV2.socialProfile, socialInteractionFrequency: socialFrequency, hobbyParticipation: activities },
        culturalProfile: { ...draft.humanIntelligenceV2.culturalProfile, religionImportance: religiousCommunity, faithTraditions: religiousCommunity === "Yes" ? [religion] : [], religiousSupportNeeds: religiousCommunity === "Yes" ? religiousNeeds : [] },
        languageProfile: { ...draft.humanIntelligenceV2.languageProfile, preferredSpokenLanguage: language, medicalDiscussionLanguage: medicalLanguage },
        foodProfile: { dietaryPreferences: dietary },
        personalityProfile: { ...draft.humanIntelligenceV2.personalityProfile, communitySizePreference: communityStyle },
        transitionRiskProfile: { ...draft.humanIntelligenceV2.transitionRiskProfile, attitudeTowardMove: moveAttitude, recentHospitalization, hospitalizationRecency: recentHospitalization === "Yes" ? hospitalTiming : "", postHospitalRehabNeed: recentHospitalization === "Yes" ? rehabNeed : "", wanderingConcerns: hasMemoryConcern ? memoryWandering : "" },
        futureCareProfile: { ...draft.humanIntelligenceV2.futureCareProfile, avoidFutureMovesPreference: continuum, continuumOfCarePreference: continuum, secureMemoryNeighborhoodNeed: hasMemoryConcern ? secureMemory : "" },
      },
    };
    setState(next);
    const params = new URLSearchParams({ budget: String(next.budget), notes: next.notes || "" });
    router.push(`/adaptive-interview?next=${encodeURIComponent(`/results?${params.toString()}`)}`);
  }

  return (
    <main className="min-h-screen bg-[#f6f3ed] px-4 py-8 text-[#26352f] sm:px-8">
      <div className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-[#397a69]">Oomnik decision questionnaire</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">We ask first. We conclude only after you confirm.</h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-[#5c665f]">Every base question is required. Follow-up questions appear only when an answer makes them relevant. The AI may clarify your answers, but it may not invent them or skip this questionnaire.</p>
        {showErrors && missing.length > 0 ? <div className="mt-6 rounded-2xl border border-amber-300 bg-amber-50 p-5"><p className="font-semibold">Please complete the following before continuing:</p><p className="mt-2 text-sm leading-6">{missing.join(", ")}.</p></div> : null}

        <div className="mt-8 space-y-6">
          <Section title="1. The person and current support">
            <div><p className="text-sm font-semibold">Who are you searching for?</p><Choices options={["Mom", "Dad", "Grandma", "Grandpa", "Spouse", "Myself", "Couple", "Relative", "Friend"]} value={draft.relationship} onChange={(value) => update({ relationship: value })} /></div>
            <div><p className="text-sm font-semibold">Age group</p><Choices options={["60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95+"]} value={draft.ageGroup} onChange={(value) => update({ ageGroup: value })} /></div>
            <div><p className="text-sm font-semibold">What daily assistance is needed? Select all that apply.</p><MultiChoices options={assistanceOptions} values={assistance} onChange={updateAssistance} /></div>
            {needsMobilityFollowUp ? <div className="grid gap-4 rounded-2xl bg-[#f1f6f3] p-4 sm:grid-cols-3"><div><p className="text-sm font-semibold">How does the person move around?</p><Choices options={["Independent", "Cane", "Walker", "Wheelchair", "Mostly in bed"]} value={medical.mobilityMethod} onChange={(value) => updateMedical({ mobilityMethod: value })} /></div><div><p className="text-sm font-semibold">Help with standing or transfers?</p><Choices options={["No", "One person", "Two people", "Mechanical lift", "Not sure"]} value={medical.transferAssistance} onChange={(value) => updateMedical({ transferAssistance: value })} /></div><div><p className="text-sm font-semibold">Any falls in the last six months?</p><Choices options={["No", "One", "More than one", "Not sure"]} value={medical.recentFalls} onChange={(value) => updateMedical({ recentFalls: value })} /></div></div> : null}
            <div><p className="text-sm font-semibold">Are there memory or confusion concerns?</p><Choices options={["No", "Occasionally forgetful", "Mild memory issues", "Significant memory issues", "Not sure"]} value={draft.memoryStatus} onChange={(value) => update({ memoryStatus: value })} /></div>
            {hasMemoryConcern ? <div className="grid gap-4 rounded-2xl bg-[#f1f6f3] p-4 sm:grid-cols-2"><div><p className="text-sm font-semibold">Any wandering concerns?</p><Choices options={["Yes", "No", "Not sure"]} value={memoryWandering} onChange={setMemoryWandering} /></div><div><p className="text-sm font-semibold">Is a secure memory setting needed?</p><Choices options={["Yes", "No", "Not sure"]} value={secureMemory} onChange={setSecureMemory} /></div></div> : null}
          </Section>

          <Section title="2. Medical needs and coordination">
            <div><p className="text-sm font-semibold">Are there ongoing medical conditions or treatments the new community must manage or coordinate?</p><Choices options={["No", "Yes", "Not sure"]} value={medical.hasOngoingMedicalNeeds} onChange={(value) => updateMedical({ hasOngoingMedicalNeeds: value, needs: value === "No" ? [] : medical.needs })} /></div>
            {needsMedicalDetails ? <><div><p className="text-sm font-semibold">Select every relevant need.</p><MultiChoices options={medicalOptions} values={medical.needs} onChange={(needs) => updateMedical({ needs })} /></div>
              {needsDialysis ? <div className="grid gap-4 sm:grid-cols-3"><Field label="Dialysis frequency" value={medical.dialysisFrequency} onChange={(value) => updateMedical({ dialysisFrequency: value })} placeholder="e.g. three times weekly" /><Field label="Current dialysis center" value={medical.dialysisCenter} onChange={(value) => updateMedical({ dialysisCenter: value })} placeholder="Name or location" /><div><p className="text-sm font-semibold">Transportation needed?</p><Choices options={["Yes", "No", "Not sure"]} value={medical.dialysisTransportation} onChange={(value) => updateMedical({ dialysisTransportation: value })} /></div></div> : null}
              {needsOxygen ? <div><p className="text-sm font-semibold">How is oxygen used?</p><Choices options={["Continuously", "At night", "As needed", "Not sure"]} value={medical.oxygenUse} onChange={(value) => updateMedical({ oxygenUse: value })} /></div> : null}
              {needsWoundCare ? <Field label="How often is wound care required?" value={medical.woundCareFrequency} onChange={(value) => updateMedical({ woundCareFrequency: value })} placeholder="Daily, three times weekly..." /> : null}
              {needsComplexDetails ? <Field label="Describe what the community must provide or coordinate" value={medical.complexConditionDetails} onChange={(value) => updateMedical({ complexConditionDetails: value })} placeholder="Condition, treatment, equipment, nursing task..." /> : null}
              <div><p className="text-sm font-semibold">Does the community need to coordinate physicians, appointments, tests, or medication changes?</p><Choices options={["Yes", "No", "Not sure"]} value={medical.physicianCoordination} onChange={(value) => updateMedical({ physicianCoordination: value })} /></div>
            </> : null}
            <div><p className="text-sm font-semibold">Has there been a recent hospitalization?</p><Choices options={["No", "Yes", "Not sure"]} value={recentHospitalization} onChange={setRecentHospitalization} /></div>
            {recentHospitalization === "Yes" ? <div className="grid gap-4 sm:grid-cols-2"><div><p className="text-sm font-semibold">How recent?</p><Choices options={["Within 30 days", "1-3 months", "3-6 months", "More than 6 months"]} value={hospitalTiming} onChange={setHospitalTiming} /></div><div><p className="text-sm font-semibold">Is rehabilitation or close monitoring needed?</p><Choices options={["Yes", "No", "Not sure"]} value={rehabNeed} onChange={setRehabNeed} /></div></div> : null}
            {rehabNeed === "Yes" ? <div><p className="text-sm font-semibold">Medicare status</p><Choices options={["Original Medicare", "Medicare Advantage", "No Medicare", "Not sure"]} value={draft.medicareStatus} onChange={(value) => update({ medicareStatus: value })} /></div> : null}
            <div><p className="text-sm font-semibold">Medicaid status</p><Choices options={["Approved", "Application pending", "May qualify", "Not eligible", "Not sure"]} value={draft.medicaidStatus} onChange={(value) => update({ medicaidStatus: value })} /></div>
          </Section>

          <Section title="3. Budget and timing">
            <label className="block text-sm font-semibold">Maximum monthly budget: ${draft.budget.toLocaleString()}<input type="range" min="3000" max="20000" step="100" value={draft.budget} onChange={(event) => update({ budget: Number(event.target.value) })} className="mt-3 block w-full accent-[#397a69]" /></label>
            <div><p className="text-sm font-semibold">When is the move expected?</p><Choices options={["Immediately", "Within 30 days", "1-3 months", "3-6 months", "Planning ahead", "Not sure"]} value={draft.moveTiming} onChange={(value) => update({ moveTiming: value })} /></div>
            <div><p className="text-sm font-semibold">How does the person feel about the move?</p><Choices options={["Wants to move", "Positive", "Cautious but open", "Anxious", "Resistant", "Not sure"]} value={moveAttitude} onChange={setMoveAttitude} /></div>
          </Section>

          <Section title="4. Lifestyle, language, and what must not be lost">
            <div><p className="text-sm font-semibold">How often is social interaction wanted?</p><Choices options={["Daily", "Several times weekly", "Weekly", "Occasionally", "Very little"]} value={socialFrequency} onChange={setSocialFrequency} /></div>
            <div><p className="text-sm font-semibold">Preferred community style</p><Choices options={["Small and familiar", "Medium", "Large and active", "Quiet", "No preference"]} value={communityStyle} onChange={setCommunityStyle} /></div>
            <div><p className="text-sm font-semibold">Which activities matter? Select all that apply.</p><MultiChoices options={activityOptions} values={activities} onChange={setActivities} /></div>
            <div><p className="text-sm font-semibold">What are you concerned may be missing after the move? Select all that apply.</p><MultiChoices options={moveConcernOptions} values={draft.moveLossConcerns} onChange={(moveLossConcerns) => update({ moveLossConcerns })} /></div>
            <Field label="Anything specific we should preserve?" value={draft.otherInterests} onChange={(value) => update({ otherInterests: value })} placeholder="A particular class, food, routine, pet, or activity" />
            <div className="grid gap-4 sm:grid-cols-2"><div><p className="text-sm font-semibold">Preferred everyday language</p><Choices options={["English", "Spanish", "Hebrew", "Russian", "Mandarin", "Arabic", "Other"]} value={language} onChange={setLanguage} /></div>{language && language !== "English" ? <Field label="Language needed for medical communication" value={medicalLanguage} onChange={setMedicalLanguage} placeholder="Language or 'English is fine'" /> : null}</div>
            <div><p className="text-sm font-semibold">Dietary requirements</p><MultiChoices options={dietaryOptions} values={dietary} onChange={setDietary} /></div>
            <div><p className="text-sm font-semibold">Is a religious community important?</p><Choices options={["No", "Yes"]} value={religiousCommunity} onChange={setReligiousCommunity} /></div>
            {religiousCommunity === "Yes" ? <div className="grid gap-4 rounded-2xl bg-[#f1f6f3] p-4 sm:grid-cols-2"><Field label="Which religion or tradition?" value={religion} onChange={setReligion} /><div><p className="text-sm font-semibold">What is needed?</p><MultiChoices options={["Services", "Place of worship", "Prayer space", "Holiday celebrations", "Dietary accommodation", "Chaplain"]} values={religiousNeeds} onChange={setReligiousNeeds} /></div></div> : null}
          </Section>

          <Section title="5. Practical requirements and future care">
            <div><p className="text-sm font-semibold">Is parking required at the residence?</p><Choices options={["No", "Regular parking", "Accessible parking", "Covered parking", "Not sure"]} value={draft.parkingRequirement} onChange={(value) => update({ parkingRequirement: value })} /></div>
            {isCouple && draft.parkingRequirement && draft.parkingRequirement !== "No" ? <div><p className="text-sm font-semibold">Parking for one or two vehicles?</p><Choices options={["One vehicle", "Two vehicles"]} value={draft.parkingVehicleCount} onChange={(value) => update({ parkingVehicleCount: value })} /></div> : null}
            <div><p className="text-sm font-semibold">Is it important to have higher levels of care available later to avoid another move?</p><Choices options={["Required", "Preferred", "Not important", "Not sure"]} value={continuum} onChange={setContinuum} /></div>
            <div><p className="text-sm font-semibold">Is location important?</p><Choices options={["Yes", "No"]} value={draft.locationImportant} onChange={(value) => update({ locationImportant: value })} /></div>
            {draft.locationImportant === "Yes" ? <div className="grid gap-4 sm:grid-cols-2"><Field label="Reference address" value={draft.referenceAddress} onChange={(value) => update({ referenceAddress: value, referenceLocationValue: value })} placeholder="Address, ZIP, city, or neighborhood" /><div><p className="text-sm font-semibold">Maximum distance</p><Choices options={["10", "20", "30", "50", "100"]} value={draft.maximumDistanceMiles} onChange={(value) => update({ maximumDistanceMiles: value })} /></div></div> : null}
          </Section>

          <Section title="6. Review and confirm what we understood">
            <div className="grid gap-3 rounded-2xl bg-[#eef5f2] p-5 text-sm leading-6 sm:grid-cols-2">
              <p><strong>Person:</strong> {draft.relationship || "Missing"}, {draft.ageGroup || "age missing"}</p>
              <p><strong>Daily support:</strong> {assistance.join(", ") || "Missing"}</p>
              <p><strong>Memory:</strong> {draft.memoryStatus || "Missing"}</p>
              <p><strong>Medical needs:</strong> {medical.hasOngoingMedicalNeeds === "No" ? "None reported" : medical.needs.join(", ") || "Missing"}</p>
              <p><strong>Budget:</strong> ${draft.budget.toLocaleString()} monthly</p>
              <p><strong>Move timing:</strong> {draft.moveTiming || "Missing"}</p>
              <p><strong>Priorities:</strong> {draft.moveLossConcerns.join(", ") || "Missing"}</p>
              <p><strong>Parking:</strong> {draft.parkingRequirement || "Missing"}</p>
              <p><strong>Language:</strong> {language || "Missing"}</p>
              <p><strong>Future care:</strong> {continuum || "Missing"}</p>
            </div>
            <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-[#cddbd5] bg-white p-4"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-1 size-5 accent-[#397a69]" /><span><strong>I confirm that this summary reflects my answers.</strong><span className="mt-1 block text-sm text-[#606a64]">I can change any answer above before continuing.</span></span></label>
          </Section>
        </div>

        <button type="button" onClick={continueToInterview} className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#397a69] px-7 py-4 text-lg font-semibold text-white hover:bg-[#2f6759]"><OomnikMark size={18} /> Continue to AI clarification</button>
      </div>
    </main>
  );
}
