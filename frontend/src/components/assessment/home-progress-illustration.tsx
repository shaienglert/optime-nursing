"use client";

import { getHomeProgress } from "@/lib/assessment-home-progress";
import type { AssessmentAnswers } from "@/lib/assessment-schema";

function progressSentence(stageId: string, ready: boolean): string {
  if (ready) return "Preparing your personalized recommendations...";
  if (stageId === "windows") return "Reviewing rehabilitation and clinical priorities...";
  if (stageId === "walls" || stageId === "access") return "Comparing levels of daily support...";
  if (stageId === "roof-frame") return "Understanding location and timing...";
  if (stageId === "roof") return "Reviewing practical preferences...";
  if (stageId === "garden" || stageId === "lights") return "Understanding everyday life and personal preferences...";
  return "Understanding your family's situation...";
}

export function HomeProgressIllustration({ answers }: { answers: AssessmentAnswers }) {
  const progress = getHomeProgress(answers);

  return (
    <section data-home-progress data-home-ready={progress.ready ? "true" : "false"} aria-label="Current assessment focus">
      <p key={progress.currentStageId} aria-live="polite" className="animate-[assessmentChoicesIn_280ms_ease-out] font-serif text-xl italic leading-8 text-[#405d53] motion-reduce:animate-none">
        {progressSentence(progress.currentStageId, progress.ready)}
      </p>
    </section>
  );
}