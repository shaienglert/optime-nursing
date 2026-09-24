"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { OomnikMark as OOmnikMark } from "@/components/brand/oomnik-mark";
import { useQuestionnaire } from "@/context/questionnaire-context";
import { buildResultsUrl } from "@/lib/results-url";
import { fetchPatientNeedsProfile, type PatientNeedsProfile } from "@/lib/api";
import { intakeInputKey, saveConfirmedIntake } from "@/lib/confirmed-intake";
import { hasUnresolvedSemanticConflict, semanticIntakeFailure } from "@/lib/semantic-conflict";

function SummaryRow({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-[#d9e3df] bg-white p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5c786f]">{label}</p><p className="mt-2 text-base leading-7 text-[#293a34]">{value || "Not provided"}</p></div>;
}

function IntakeConfirmationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, setState } = useQuestionnaire();
  const [confirmationRequested, setConfirmationRequested] = useState(false);
  const [reviewed, setReviewed] = useState<{ key: string; profile: PatientNeedsProfile } | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [additionalContext, setAdditionalContext] = useState("");
  const inputKey = intakeInputKey(state as unknown as Record<string, unknown>, state.notes || "");
  const requestedDestination = searchParams.get("next")?.startsWith("/results") ? String(searchParams.get("next")) : "/results";

  useEffect(() => {
    let active = true;
    void fetchPatientNeedsProfile({ questionnaire_state: state as unknown as Record<string, unknown>, natural_language_query: state.notes || "" }).then(profile => {
      if (!active) return;
      const canonical = profile.decision_intelligence?.canonical_decision_state as { authoritative?: boolean; client?: string; system?: string } | undefined;
      const human = profile.decision_intelligence?.human_intelligence as { semantic_ai?: { status?: string; result?: { statements?: unknown } } } | undefined;
      if (!profile.intake_profile_id || canonical?.authoritative !== true || canonical.client !== "COMPLETE" || canonical.system === "BLOCKED" || semanticIntakeFailure(human?.semantic_ai) || hasUnresolvedSemanticConflict(human?.semantic_ai?.result?.statements)) {
        setReviewError("We need to finish reviewing your answers before you can confirm. Return to the conversation to continue.");
        return;
      }
      setReviewError(null);
      setReviewed({ key: inputKey, profile });
    }).catch(error => { if (active) setReviewError(error instanceof Error ? error.message : "Unable to prepare your profile."); });
    return () => { active = false; };
    // Confirmation acknowledgement is deliberately excluded from the case key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputKey, retry]);

  useEffect(() => {
    const structuredComplete =
      state.questionnaireCompletion?.mandatoryComplete &&
      state.questionnaireCompletion?.conditionalFollowUpsComplete;
    if (!structuredComplete && !state.notes?.trim()) {
      router.replace("/intake");
    }
  }, [router, state.notes, state.questionnaireCompletion]);

  useEffect(() => {
    if (!confirmationRequested || !state.questionnaireCompletion.clientSummaryConfirmed) return;
    const requestedPathname = requestedDestination.split("?", 1)[0] || "/results";
    router.replace(buildResultsUrl(state, requestedPathname));
  }, [confirmationRequested, requestedDestination, router, state]);

  function addContext() {
    const extra = additionalContext.trim();
    if (!extra) return;
    setState((current) => ({ ...current, notes: [current.notes?.trim(), extra].filter(Boolean).join("\n\n"), questionnaireCompletion: { ...current.questionnaireCompletion, clientSummaryConfirmed: false, confirmedAt: "" } }));
    setAdditionalContext("");
    setReviewed(null);
    setRetry((value) => value + 1);
  }

  function confirm() {
    if (reviewError || reviewed?.key !== inputKey || !reviewed.profile.intake_profile_id) return;
    try { saveConfirmedIntake(reviewed.profile.intake_profile_id, inputKey); }
    catch (error) { setReviewError(error instanceof Error ? error.message : "Unable to save your confirmation."); return; }
    setState((current) => ({
        ...current,
        questionnaireCompletion: {
          ...current.questionnaireCompletion,
          // Reaching this screen means the governed AI declared the client profile
          // complete. Confirmation seals either the structured or narrative route.
          mandatoryComplete: true,
          conditionalFollowUpsComplete: true,
          clientSummaryConfirmed: true,
          confirmedAt: new Date().toISOString(),
        },
      }));
    // Navigate only after the provider has committed the confirmed profile.
    // Reading a variable assigned inside a state updater races React scheduling.
    setConfirmationRequested(true);
  }

  const medical = state.medicalCareProfile;
  const hi = state.humanIntelligenceV2;

  return (
    <main className="min-h-screen bg-[#f6f3ed] px-4 py-10 text-[#26352f] sm:px-8">
      <section className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-[#397a69]">Final understanding check</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">Please confirm what OOmnik understood.</h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-[#5c665f]">This confirmed profile—not free-text guesses—will be the basis for research, matching, and the questions shown for each community.</p>
        {reviewError ? <div role="alert" className="mt-6 rounded-2xl bg-amber-50 p-5 text-lg">{reviewError} <button type="button" onClick={() => { setReviewed(null); setRetry(value => value + 1); }} className="ml-3 underline">Try again</button> <button type="button" onClick={() => router.push("/adaptive-interview?next=%2Fresults")} className="ml-3 underline">Continue our conversation</button></div>
          : reviewed?.key !== inputKey ? <p role="status" className="mt-6 text-xl">Preparing the profile for your review…</p>
          : <section className="mt-6 rounded-2xl bg-white p-5"><h2 className="text-2xl font-semibold">Needs used in your search</h2><ul className="mt-3 space-y-2 text-lg">{reviewed.profile.needs.map((need, index) => <li key={`${need.parameter_id}-${index}`}>{need.need_text}</li>)}</ul></section>}

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {state.notes?.trim() ? <div className="sm:col-span-2"><SummaryRow label="Story provided" value={state.notes} /></div> : null}
          <SummaryRow label="Person" value={[state.relationship, state.ageGroup].filter(Boolean).join(", ")} />
          <SummaryRow label="Daily support" value={state.relationship === "Couple" ? state.coupleAssistance || state.assistanceLevel : state.assistanceLevel} />
          <SummaryRow label="Mobility" value={[medical.mobilityMethod, medical.transferAssistance ? `Transfers: ${medical.transferAssistance}` : "", medical.recentFalls ? `Falls: ${medical.recentFalls}` : ""].filter(Boolean).join("; ")} />
          <SummaryRow label="Memory and safety" value={[state.memoryStatus, hi.transitionRiskProfile.wanderingConcerns ? `Wandering: ${hi.transitionRiskProfile.wanderingConcerns}` : "", hi.futureCareProfile.secureMemoryNeighborhoodNeed ? `Secure setting: ${hi.futureCareProfile.secureMemoryNeighborhoodNeed}` : ""].filter(Boolean).join("; ")} />
          <SummaryRow label="Medical needs" value={medical.hasOngoingMedicalNeeds === "No" ? "No ongoing medical needs reported" : medical.needs.join(", ")} />
          <SummaryRow label="Medical coordination" value={[medical.physicianCoordination, medical.dialysisFrequency, medical.oxygenUse, medical.woundCareFrequency, medical.complexConditionDetails].filter(Boolean).join("; ")} />
          <SummaryRow label="Coverage and budget" value={[state.budget > 0 ? `$${state.budget.toLocaleString()} per month` : "Budget: Not provided", `Medicare: ${state.medicareStatus || "Not provided"}`, `Medicaid: ${state.medicaidStatus || "Not provided"}`].join("; ")} />
          <SummaryRow label="Timing and transition" value={[state.moveTiming, hi.transitionRiskProfile.attitudeTowardMove].filter(Boolean).join("; ")} />
          <SummaryRow label="Lifestyle priorities" value={[hi.familyProfile.socialInteractionNeed, hi.personalityProfile.communitySizePreference, ...state.happinessPreferences, ...state.moveLossConcerns].filter(Boolean).join(", ")} />
          <SummaryRow label="Language, diet, and religion" value={[hi.languageProfile.preferredSpokenLanguage, ...hi.foodProfile.dietaryPreferences, hi.culturalProfile.religionImportance === "Yes" ? hi.culturalProfile.faithTraditions.join(", ") : hi.culturalProfile.religionImportance === "No" ? "No religious-community requirement" : "Religious-community preference: Not provided"].filter(Boolean).join("; ")} />
          <SummaryRow label="Practical requirements" value={[state.parkingRequirement ? `Parking: ${state.parkingRequirement}` : "Parking: Not provided", state.parkingVehicleCount, hi.futureCareProfile.continuumOfCarePreference ? `Future care continuity: ${hi.futureCareProfile.continuumOfCarePreference}` : "Future care continuity: Not provided"].filter(Boolean).join("; ")} />
          <SummaryRow label="Location" value={
            state.locationImportant === "No"
              ? "No location constraint"
              : [
                  state.referenceAddress || state.referenceLocationValue,
                  state.maximumDistanceMiles ? `within ${state.maximumDistanceMiles} miles` : "",
                ].filter(Boolean).join("; ")
          } />
        </div>

        <section className="mt-10 rounded-3xl border border-[#d9e3df] bg-white p-6">
          <h2 className="text-2xl font-semibold">Anything you’d like to add or correct?</h2>
          <p className="mt-2 text-lg leading-8 text-[#5c665f]">Add anything in your own words. OOmnik will read it together with your answers and prepare an updated understanding for you to approve.</p>
          <textarea value={additionalContext} onChange={(event) => setAdditionalContext(event.target.value)} rows={4} className="mt-5 w-full resize-y rounded-2xl border border-[#b9cbc4] bg-[#fbfaf7] p-4 text-xl leading-8 outline-none focus:border-[#397a69]" placeholder="Add a preference, concern, correction, or anything we missed…" />
          <button type="button" onClick={addContext} disabled={!additionalContext.trim()} className="mt-4 rounded-full border border-[#397a69] px-6 py-3 text-lg font-semibold text-[#315f53] disabled:opacity-40">Update my summary</button>
        </section>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <button type="button" onClick={() => router.push("/intake")} className="rounded-full border border-[#76958a] bg-white px-7 py-4 text-base font-semibold text-[#315f53]">Change answers</button>
          <button type="button" onClick={confirm} disabled={!!reviewError || reviewed?.key !== inputKey || confirmationRequested} className="inline-flex items-center gap-2 rounded-full bg-[#397a69] px-7 py-4 text-base font-semibold text-white hover:bg-[#2f6759] disabled:opacity-40"><OOmnikMark size={16} /> I confirm—show recommendations</button>
        </div>
      </section>
    </main>
  );
}

export default function IntakeConfirmationPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-[#f6f3ed] px-6 py-12 text-xl text-[#5c665f]">Preparing your summary…</main>}>
      <IntakeConfirmationContent />
    </Suspense>
  );
}
