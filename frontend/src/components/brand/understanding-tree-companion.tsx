"use client";

import { usePathname } from "next/navigation";

import { TreeOfUnderstanding } from "@/app/intake/tree-of-understanding";
import { useQuestionnaire } from "@/context/questionnaire-context";

/** Keeps the same understanding signal visible from the first homepage answer. */
export function UnderstandingTreeCompanion() {
  const pathname = usePathname();
  const { state } = useQuestionnaire();

  if (pathname !== "/") return null;

  const domains = [
    { id: "person", label: "Person", understood: Boolean(state.relationship || state.ageGroup) },
    { id: "care", label: "Care needs", understood: Boolean(state.assistanceLevel || state.memoryStatus) },
    { id: "daily-life", label: "Daily life", understood: Boolean(state.otherInterests || state.notes) },
    { id: "family", label: "Family support", understood: Boolean(state.distanceFromFamily) },
    { id: "location", label: "Location", understood: Boolean(state.referenceAddress || state.locationImportant) },
    { id: "budget", label: "Budget", understood: Boolean(state.budget) },
  ];

  return (
    <div className="pointer-events-none fixed right-5 top-24 z-40 hidden w-[19rem] xl:block 2xl:right-10">
      <div className="pointer-events-auto rounded-[2rem] border border-[#d9e8df] bg-white/88 p-4 shadow-[0_24px_70px_rgba(45,99,80,0.13)] backdrop-blur-xl">
        <TreeOfUnderstanding domains={domains} />
      </div>
    </div>
  );
}
