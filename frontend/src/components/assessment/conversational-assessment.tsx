"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { AssessmentProgress } from "@/components/assessment/assessment-progress";
import { ConversationQuestion } from "@/components/assessment/conversation-question";
import { EditableAnswerSummary } from "@/components/assessment/editable-answer-summary";
import { ProgressiveSection } from "@/components/assessment/progressive-section";
import { UnknownClarificationList } from "@/components/assessment/unknown-clarification-list";
import { ValidationMessage } from "@/components/assessment/validation-message";
import {
  ASSESSMENT_SECTIONS,
  advisorResponseFor,
  buildAssessmentSummary,
  getAssessmentSection,
  getConversationQuestions,
  getProgressiveQuestions,
  getUnknownClarifications,
  hasAssessmentAnswer,
  pruneHiddenAssessmentAnswers,
} from "@/lib/assessment-conversation";
import type { AssessmentAnswer, AssessmentAnswers } from "@/lib/assessment-schema";

export function ConversationalAssessment({ answers, validation, submitting, onAnswersChange, onCurrentQuestionChange, onSubmit }: {
  answers: AssessmentAnswers;
  validation: string;
  submitting: boolean;
  onAnswersChange: (answers: AssessmentAnswers) => void;
  onCurrentQuestionChange: (questionId: string) => void;
  onSubmit: () => Promise<void>;
}) {
  const [clearedNotice, setClearedNotice] = useState("");
  const [announcement, setAnnouncement] = useState("");
  const [pendingScrollId, setPendingScrollId] = useState<string | null>(null);
  const questionElements = useRef(new Map<string, HTMLElement>());
  const visibleQuestions = useMemo(() => getConversationQuestions(answers), [answers]);
  const revealedQuestions = useMemo(() => getProgressiveQuestions(answers), [answers]);
  const currentQuestion = visibleQuestions.find((question) => !hasAssessmentAnswer(answers[question.id])) || visibleQuestions.at(-1);
  const completedRequired = visibleQuestions.filter((question) => question.required && hasAssessmentAnswer(answers[question.id])).length;
  const requiredCount = visibleQuestions.filter((question) => question.required).length;
  const percentage = requiredCount ? Math.round((completedRequired / requiredCount) * 100) : 0;
  const complete = visibleQuestions.length > 0 && visibleQuestions.every((question) => hasAssessmentAnswer(answers[question.id]));

  useEffect(() => {
    if (!pendingScrollId) return;
    const element = questionElements.current.get(pendingScrollId);
    if (!element) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    element.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "center" });
  }, [pendingScrollId, revealedQuestions.length]);

  const commitAnswer = (questionId: string, answer: AssessmentAnswer) => {
    const previouslyRevealed = new Set(revealedQuestions.map((question) => question.id));
    const pruned = pruneHiddenAssessmentAnswers({ ...answers, [questionId]: answer });
    const nextQuestions = getProgressiveQuestions(pruned.answers);
    const newlyRevealed = nextQuestions.find((question) => !previouslyRevealed.has(question.id));
    const nextCurrent = getConversationQuestions(pruned.answers).find((question) => !hasAssessmentAnswer(pruned.answers[question.id]));
    onAnswersChange(pruned.answers);
    if (nextCurrent) onCurrentQuestionChange(nextCurrent.id);
    setClearedNotice(pruned.clearedQuestionIds.length ? `${pruned.clearedQuestionIds.length} answer${pruned.clearedQuestionIds.length === 1 ? " was" : "s were"} cleared because ${pruned.clearedQuestionIds.length === 1 ? "it no longer applies" : "they no longer apply"}.` : "");
    if (newlyRevealed) {
      setAnnouncement(`Next question: ${newlyRevealed.englishLabel}`);
      setPendingScrollId(newlyRevealed.id);
    }
  };

  const editQuestion = (questionId: string) => {
    onCurrentQuestionChange(questionId);
    setPendingScrollId(questionId);
    questionElements.current.get(questionId)?.focus({ preventScroll: true });
  };

  const currentSection = currentQuestion ? getAssessmentSection(currentQuestion).label : ASSESSMENT_SECTIONS.at(-1)?.label || "Assessment";

  return (
    <>
      <AssessmentProgress percentage={percentage} section={currentSection} completed={completedRequired} required={requiredCount} />
      <p className="sr-only" aria-live="polite">{announcement}</p>
      {clearedNotice ? <p role="status" className="mt-5 border-l-2 border-[#bd8b45] bg-[#fff8ec] px-4 py-3 text-sm text-[#74562e]">{clearedNotice}</p> : null}

      {ASSESSMENT_SECTIONS.filter((section) => section.id !== "summary").map((section) => {
        const questions = revealedQuestions.filter((question) => getAssessmentSection(question).id === section.id);
        if (!questions.length) return null;
        return (
          <ProgressiveSection key={section.id} label={section.label}>
            {questions.map((question) => (
              <div key={`${question.id}:${JSON.stringify(answers[question.id])}`} ref={(node) => { if (node) questionElements.current.set(question.id, node); else questionElements.current.delete(question.id); }}>
                <ConversationQuestion question={question} answer={answers[question.id]} advisorResponse={advisorResponseFor(question, answers)} current={currentQuestion?.id === question.id} onCommit={(answer) => commitAnswer(question.id, answer)} />
              </div>
            ))}
          </ProgressiveSection>
        );
      })}

      {complete ? (
        <section className="mt-12 scroll-mt-32 border-t-2 border-[#8db6a7] pt-9" aria-labelledby="understood-heading">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#397261]">What OPTIME understood</p>
          <h2 id="understood-heading" className="mt-3 text-3xl font-semibold text-[#18342a]">What I understand so far</h2>
          <p className="mt-4 text-lg leading-8 text-[#405d53]">{buildAssessmentSummary(answers)}</p>
          <div className="mt-8"><EditableAnswerSummary questions={visibleQuestions} answers={answers} onEdit={editQuestion} /></div>
          <UnknownClarificationList questions={getUnknownClarifications(answers)} onEdit={editQuestion} />
          <ValidationMessage message={validation} />
          <div className="mt-8 flex flex-col gap-3 border-t border-[#d9e5e0] pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-[#62766e]">Your answers stay private on this device until you submit.</p>
            <button type="button" disabled={submitting} onClick={() => void onSubmit()} className="bg-[#236f5d] px-6 py-3 text-sm font-semibold text-white outline-offset-4 hover:bg-[#195a4b] focus-visible:outline-2 focus-visible:outline-[#236f5d] disabled:cursor-wait disabled:opacity-60">{submitting ? "Creating your matches..." : "Find matching facilities"}</button>
          </div>
        </section>
      ) : <ValidationMessage message={validation} />}

      <div className="mt-8 flex items-center justify-between gap-4 border-t border-[#dfe8e4] pt-5 text-xs text-[#6b7d76]"><span>Saved automatically on this device.</span><Link href="/" className="font-semibold text-[#2a6858] underline underline-offset-4">Return home</Link></div>
    </>
  );
}