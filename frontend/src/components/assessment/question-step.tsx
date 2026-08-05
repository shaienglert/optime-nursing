import type { ReactNode } from "react";

import { MultiSelect } from "@/components/assessment/multi-select";
import { OptionCard } from "@/components/assessment/option-card";
import { PagedOptionList } from "@/components/assessment/paged-option-list";
import { PriorityRanking } from "@/components/assessment/priority-ranking";
import { hasAssessmentAnswer } from "@/lib/assessment-conversation";
import { UNKNOWN_FROM_FAMILY, type AssessmentAnswer, type AssessmentOption, type AssessmentQuestion } from "@/lib/assessment-schema";

const UNKNOWN_OPTION: AssessmentOption = {
  value: UNKNOWN_FROM_FAMILY,
  label: "Not sure",
  hebrewLabel: "לא בטוח/ה",
  description: "No problem. We’ll keep this unknown and verify it later if needed.",
};

function optionsWithUnknown(question: AssessmentQuestion): AssessmentOption[] {
  const options = question.options || [];
  if (question.id === "continue_method" || options.some((option) => option.value === UNKNOWN_FROM_FAMILY)) return options;
  return [...options, UNKNOWN_OPTION];
}

export function QuestionStep({ question, prompt, accessiblePrompt, answer, choicesVisible = true, onChange, onFinish }: {
  question: AssessmentQuestion;
  prompt: ReactNode;
  accessiblePrompt?: string;
  answer: AssessmentAnswer | undefined;
  choicesVisible?: boolean;
  onChange: (answer: AssessmentAnswer) => void;
  onFinish?: () => void;
}) {
  const answerText = typeof answer === "string" ? answer : "";

  return (
    <fieldset>
      <legend aria-label={accessiblePrompt} className="font-serif text-2xl font-semibold leading-9 text-[#1d332c] sm:text-3xl">{prompt}</legend>
      {choicesVisible ? <p className="mt-3 max-w-2xl text-lg leading-7 text-[#526a62]">{question.helpText}</p> : null}
      {choicesVisible ? <div data-answer-choices className="mt-5 animate-[assessmentChoicesIn_280ms_ease-out] motion-reduce:animate-none">
        {question.answerType === "single" && question.options ? <PagedOptionList options={optionsWithUnknown(question)} selectedValues={typeof answer === "string" ? [answer] : []}>{(option) => <OptionCard key={option.value} option={option} selected={answer === option.value} onSelect={() => onChange(option.value)} />}</PagedOptionList> : null}
        {question.answerType === "multi" && question.options ? <MultiSelect options={optionsWithUnknown(question)} value={Array.isArray(answer) ? answer : []} maxSelections={question.maxSelections} onChange={onChange} /> : null}
        {question.answerType === "priority" && question.options ? <PriorityRanking options={question.options} value={Array.isArray(answer) ? answer : []} maxSelections={question.maxSelections} onChange={onChange} /> : null}
        {question.answerType === "text" ? <input type={question.id === "contact_email" ? "email" : "text"} autoComplete={question.id === "contact_email" ? "email" : "off"} value={answerText} onChange={(event) => onChange(event.target.value)} onBlur={onFinish} onKeyDown={(event) => { if (event.key === "Enter") onFinish?.(); }} placeholder={question.placeholder} className="min-h-14 w-full rounded-lg border-2 border-[#9db9af] bg-white px-5 py-3 text-lg text-[#203a32] outline-none focus:border-[#1f6f5d] focus:ring-3 focus:ring-[#b9dbd0]" /> : null}
        {question.answerType === "number" ? <input type="number" value={typeof answer === "number" ? answer : ""} onChange={(event) => onChange(Number(event.target.value))} onBlur={onFinish} onKeyDown={(event) => { if (event.key === "Enter") onFinish?.(); }} className="w-full rounded-lg border-2 border-[#9db9af] bg-white px-5 py-3.5 text-lg outline-none focus:border-[#1f6f5d] focus:ring-3 focus:ring-[#b9dbd0]" /> : null}
        {question.answerType === "multi" || question.answerType === "priority" ? (
          <div className="mt-7 flex justify-end">
            <button
              type="button"
              onClick={onFinish}
              disabled={!hasAssessmentAnswer(answer)}
              className="min-h-12 bg-[#2f6f5e] px-7 py-3 text-base font-semibold text-white transition-colors hover:bg-[#25594c] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#2f6f5e] disabled:cursor-not-allowed disabled:bg-[#b7c3be]"
            >
              Next
            </button>
          </div>
        ) : null}
      </div> : null}
    </fieldset>
  );
}