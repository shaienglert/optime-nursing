"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { buildResultsUrl } from "@/lib/results-url";

function SummaryRow({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-[#d9e3df] bg-white p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5c786f]">{label}</p><p className="mt-2 text-base leading-7 text-[#293a34]">{value || "Not provided"}</p></div>;
}

function IntakeConfirmationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, setState } = useQuestionnaire();
  const requestedDestination = searchParams.get("next")?.startsWith("/results") ? String(searchParams.get("next")) : "/results";

  useEffect(() => {
    const structuredComplete =
      state.questionnaireCompletion?.mandatoryComplete &&
      state.questionnaireCompletion?.conditionalFollowUpsComplete;
    if (!structuredComplete && !state.notes?.trim()) {
      router.replace("/intake");
    }
  }, [router, state.notes, state.questionnaireCompletion]);

  function confirm() {
    let confirmedState = state;
    setState((current) => {
      confirmedState = {
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
      };
      return confirmedState;
    });
    const requestedPathname = requestedDestination.split("?", 1)[0] || "/results";
    router.replace(buildResultsUrl(confirmedState, requestedPathname));
  }

  const medical = state.medicalCareProfile;
  const hi = state.humanIntelligenceV2;

  return (
    <main className="min-h-screen bg-[#f6f3ed] px-4 py-10 text-[#26352f] sm:px-8">
      <section className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-[#397a69]">Final understanding check</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">Please confirm what Oomnik understood.</h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-[#5c665f]">This confirmed profile—not free-text guesses—will be the basis for research, matching, and the questions shown for each community.</p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {state.notes?.trim() ? <div className="sm:col-span-2"><SummaryRow label="Story provided" value={state.notes} /></div> : null}
          <SummaryRow label="Person" value={[state.relationship, state.ageGroup].filter(Boolean).join(", ")} />
          <SummaryRow label="Daily support" value={state.assistanceLevel} />
          <SummaryRow label="Mobility" value={[medical.mobilityMethod, medical.transferAssistance ? `Transfers: ${medical.transferAssistance}` : "", medical.recentFalls ? `Falls: ${medical.recentFalls}` : ""].filter(Boolean).join("; ")} />
          <SummaryRow label="Memory and safety" value={[state.memoryStatus, hi.transitionRiskProfile.wanderingConcerns ? `Wandering: ${hi.transitionRiskProfile.wanderingConcerns}` : "", hi.futureCareProfile.secureMemoryNeighborhoodNeed ? `Secure setting: ${hi.futureCareProfile.secureMemoryNeighborhoodNeed}` : ""].filter(Boolean).join("; ")} />
          <SummaryRow label="Medical needs" value={medical.hasOngoingMedicalNeeds === "No" ? "No ongoing medical needs reported" : medical.needs.join(", ")} />
          <SummaryRow label="Medical coordination" value={[medical.physicianCoordination, medical.dialysisFrequency, medical.oxygenUse, medical.woundCareFrequency, medical.complexConditionDetails].filter(Boolean).join("; ")} />
          <SummaryRow label="Coverage and budget" value={[`$${state.budget.toLocaleString()} per month`, `Medicare: ${state.medicareStatus || "Not provided"}`, `Medicaid: ${state.medicaidStatus || "Not provided"}`].join("; ")} />
          <SummaryRow label="Timing and transition" value={[state.moveTiming, hi.transitionRiskProfile.attitudeTowardMove].filter(Boolean).join("; ")} />
          <SummaryRow label="Lifestyle priorities" value={[...state.happinessPreferences, ...state.moveLossConcerns].join(", ")} />
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

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <button type="button" onClick={() => router.push("/intake")} className="rounded-full border border-[#76958a] bg-white px-7 py-4 text-base font-semibold text-[#315f53]">Change answers</button>
          <button type="button" onClick={confirm} className="rounded-full bg-[#397a69] px-7 py-4 text-base font-semibold text-white hover:bg-[#2f6759]">I confirm—show recommendations</button>
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
