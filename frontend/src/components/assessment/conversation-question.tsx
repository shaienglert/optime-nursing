"use client";

import { useState } from "react";

import { AdvisorResponse } from "@/components/assessment/advisor-response";
import { QuestionStep } from "@/components/assessment/question-step";
import { hasAssessmentAnswer } from "@/lib/assessment-conversation";
import type { AssessmentAnswer, AssessmentQuestion } from "@/lib/assessment-schema";

export function ConversationQuestion({ question, answer, advisorResponse, current, onCommit }: {
  question: AssessmentQuestion;
  answer: AssessmentAnswer | undefined;
  advisorResponse: string;
  current: boolean;
  onCommit: (answer: AssessmentAnswer) => void;
}) {
  const [draftAnswer, setDraftAnswer] = useState<AssessmentAnswer | undefined>(answer);

  const requiresConfirmation = ["multi", "priority", "text", "number"].includes(question.answerType);
  const handleChange = (next: AssessmentAnswer) => {
    setDraftAnswer(next);
    if (!requiresConfirmation) onCommit(next);
  };
  const canConfirm = !question.required || hasAssessmentAnswer(draftAnswer);

  return (
    <article data-question-id={question.id} tabIndex={-1} className={`scroll-mt-36 border bg-white px-5 py-6 shadow-[0_18px_55px_-44px_rgba(29,63,52,0.7)] outline-none transition sm:px-7 sm:py-8 motion-reduce:transition-none ${current ? "border-[#a8c9bd]" : "border-[#dfe8e4]"}`}>
      <AdvisorResponse>{advisorResponse}</AdvisorResponse>
      <div className="mt-6">
        <QuestionStep question={question} answer={draftAnswer} onChange={handleChange} />
      </div>
      {requiresConfirmation ? (
        <div className="mt-6 flex justify-end">
          <button type="button" disabled={!canConfirm} onClick={() => draftAnswer !== undefined && onCommit(draftAnswer)} className="bg-[#236f5d] px-5 py-2.5 text-sm font-semibold text-white outline-offset-4 hover:bg-[#195a4b] focus-visible:outline-2 focus-visible:outline-[#236f5d] disabled:cursor-not-allowed disabled:opacity-40">
            {current ? "Continue" : "Save changes"}
          </button>
        </div>
      ) : null}
    </article>
  );
}