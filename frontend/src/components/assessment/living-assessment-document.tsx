import type { RefObject } from "react";

import { ConversationQuestion } from "@/components/assessment/conversation-question";
import { buildAdvisorPrompt, type AdvisorTurn } from "@/lib/assessment-advisor";
import { advisorResponseFor, assessmentAnswerLabel, completedAnswerSentence } from "@/lib/assessment-conversation";
import type { AssessmentAnswer, AssessmentAnswers, AssessmentQuestion } from "@/lib/assessment-schema";

export function CompletedDecisionEntry({ question, answers, editing, onEdit, onCommit }: {
  question: AssessmentQuestion;
  answers: AssessmentAnswers;
  editing: boolean;
  onEdit: () => void;
  onCommit: (answer: AssessmentAnswer) => void;
}) {
  if (editing) {
    return (
      <ConversationQuestion
        key={`${question.id}:${JSON.stringify(answers[question.id])}`}
        question={question}
        prompt={question.englishLabel}
        answer={answers[question.id]}
        advisorResponse="Let’s revise this sentence and carry the change through the rest of the document."
        current={false}
        onCommit={onCommit}
      />
    );
  }

  return (
    <div className="flex items-start gap-3 border-l-2 border-[#bfd0c8] pl-5 sm:pl-7">
      <div className="min-w-0 flex-1">
        <p className="text-base leading-7 text-[#716c64]">{buildAdvisorPrompt(question, answers)}</p>
        <p data-selected-answer className="mt-3 text-lg font-semibold leading-8 text-[#36574c]"><span aria-hidden="true" className="mr-2 text-[#2f6f5e]">✓</span>{assessmentAnswerLabel(question, answers)}</p>
        <p className="mt-4 font-serif text-xl leading-8 text-[#34312c]">{completedAnswerSentence(question, answers)}</p>
        <p className="mt-3 text-lg leading-8 text-[#625d55]">{advisorResponseFor(question, answers)}</p>
        {question.id === "who_needs_care" ? <p className="mt-2 text-lg leading-8 text-[#625d55]">Because we&apos;re looking for {assessmentAnswerLabel(question, answers).toLowerCase()}, I&apos;ll personalize every question around their situation.</p> : null}
        <button type="button" onClick={onEdit} className="mt-3 min-h-11 text-lg font-semibold text-[#526a62] underline decoration-[#8ea49b] underline-offset-4 transition hover:text-[#2f6f5e]">
          Edit this detail
        </button>
      </div>
    </div>
  );
}

export function ActiveContextualQuestion({ advisorTurn, answers, activeTurn, onDraftChange, onCommit }: {
  advisorTurn: AdvisorTurn;
  answers: AssessmentAnswers;
  activeTurn: RefObject<HTMLElement | null>;
  onDraftChange: (answer: AssessmentAnswer) => void;
  onCommit: (answer: AssessmentAnswer) => void;
}) {
  const question = advisorTurn.question;
  return (
    <section ref={activeTurn} data-next-question-id={question.id} data-conversation-question-id={question.id} aria-label="The next part of your family document" className="scroll-mt-24">
      <ConversationQuestion
        key={question.id}
        question={question}
        prompt={advisorTurn.prompt || question.englishLabel}
        answer={answers[question.id]}
        advisorResponse={advisorResponseFor(question, answers)}
        current
        onDraftChange={onDraftChange}
        onCommit={onCommit}
      />
    </section>
  );
}

export function LivingAssessmentDocument({ answeredQuestions, answers, advisorTurn, editingQuestionId, activeTurn, onEdit, onDraftChange, onCommit }: {
  answeredQuestions: AssessmentQuestion[];
  answers: AssessmentAnswers;
  advisorTurn: AdvisorTurn | null;
  editingQuestionId: string | null;
  activeTurn: RefObject<HTMLElement | null>;
  onEdit: (questionId: string) => void;
  onDraftChange: (questionId: string, answer: AssessmentAnswer) => void;
  onCommit: (questionId: string, answer: AssessmentAnswer) => void;
}) {
  return (
    <div data-conversation-sequence className="space-y-8">
      {answeredQuestions.map((question) => (
        <section key={question.id} data-answered-question-id={question.id} data-conversation-question-id={question.id} className="pb-16 sm:pb-0">
          <CompletedDecisionEntry
            question={question}
            answers={answers}
            editing={editingQuestionId === question.id}
            onEdit={() => onEdit(question.id)}
            onCommit={(answer) => onCommit(question.id, answer)}
          />
        </section>
      ))}
      {advisorTurn ? <ActiveContextualQuestion advisorTurn={advisorTurn} answers={answers} activeTurn={activeTurn} onDraftChange={(answer) => onDraftChange(advisorTurn.question.id, answer)} onCommit={(answer) => onCommit(advisorTurn.question.id, answer)} /> : null}
    </div>
  );
}