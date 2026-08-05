"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { LivingAssessmentDocument } from "@/components/assessment/living-assessment-document";
import { MatchReadinessAction } from "@/components/assessment/match-readiness-action";
import { AdvisorWritingBlock } from "@/components/assessment/advisor-writing-block";
import { ValidationMessage } from "@/components/assessment/validation-message";
import { buildAdvisorCompletionSummary, isAdvisorReadyForMatch, selectAdvisorTurn, type AdvisorTurn } from "@/lib/assessment-advisor";
import {
  getConversationQuestions,
  hasAssessmentAnswer,
  pruneHiddenAssessmentAnswers,
} from "@/lib/assessment-conversation";
import type { AssessmentAnswer, AssessmentAnswers, AssessmentQuestion } from "@/lib/assessment-schema";

export function ConversationalAssessment({ answers, validation, submitting, recommendationsReady, onAnswersChange, onCurrentQuestionChange, onSubmit }: {
  answers: AssessmentAnswers;
  validation: string;
  submitting: boolean;
  recommendationsReady: boolean;
  onAnswersChange: (answers: AssessmentAnswers) => void;
  onCurrentQuestionChange: (questionId: string) => void;
  onSubmit: () => Promise<void>;
}) {
  const [clearedNotice, setClearedNotice] = useState("");
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [settlingTurn, setSettlingTurn] = useState<AdvisorTurn | null>(null);
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

  const saveDraftAnswer = (questionId: string, answer: AssessmentAnswer) => {
    const pruned = pruneHiddenAssessmentAnswers({ ...answers, [questionId]: answer });
    if (advisorTurn?.question.id === questionId) setSettlingTurn(advisorTurn);
    onAnswersChange(pruned.answers);
    setClearedNotice(pruned.clearedQuestionIds.length ? "I removed a detail that no longer applies after this update." : "");
  };

  const editQuestion = (questionId: string) => {
    setEditingQuestionId(questionId);
  };

  const activateMatch = () => {
    if (recommendationsReady) {
      document.getElementById("recommendations-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    void onSubmit();
  };

  return (
    <div className="space-y-12 sm:space-y-16">
      <section className="border-t-2 border-[#2f4d43] pt-9">
        <h2 className="font-serif text-2xl text-[#292722] sm:text-3xl">Understanding</h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-[#625d55]">
          We&apos;ll begin with the person at the center of this decision. Each answer will become part of this document, and anything uncertain will remain open rather than being guessed.
        </p>
      </section>

      <LivingAssessmentDocument
        answeredQuestions={answeredQuestions}
        answers={answers}
        advisorTurn={advisorTurn}
        editingQuestionId={editingQuestionId}
        activeTurn={activeTurn}
        onEdit={editQuestion}
        onDraftChange={saveDraftAnswer}
        onCommit={commitAnswer}
      />

      {clearedNotice ? <p role="status" className="border-l-2 border-[#c99c55] pl-5 text-lg leading-8 text-[#725c39]">{clearedNotice}</p> : null}

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

      <p className="border-t border-[#dedbd4] pt-6 text-lg leading-7 text-[#625d55]">This document is saved automatically on this device while you work.</p>
    </div>
  );
}