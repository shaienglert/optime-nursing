import { MultiSelect } from "@/components/assessment/multi-select";
import { OptionCard } from "@/components/assessment/option-card";
import { PriorityRanking } from "@/components/assessment/priority-ranking";
import type { AssessmentAnswer, AssessmentQuestion } from "@/lib/assessment-schema";

export function QuestionStep({ question, answer, onChange }: { question: AssessmentQuestion; answer: AssessmentAnswer | undefined; onChange: (answer: AssessmentAnswer) => void }) {
  return (
    <fieldset>
      <legend className="text-2xl font-semibold tracking-[-0.02em] text-[#1d332c] sm:text-3xl">{question.englishLabel}</legend>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-[#60756e]">{question.helpText}</p>
      <div className="mt-6">
        {question.answerType === "single" && question.options ? <div className="grid gap-2 sm:grid-cols-2">{question.options.map((option) => <OptionCard key={option.value} option={option} selected={answer === option.value} onSelect={() => onChange(option.value)} />)}</div> : null}
        {question.answerType === "multi" && question.options ? <MultiSelect options={question.options} value={Array.isArray(answer) ? answer : []} maxSelections={question.maxSelections} onChange={onChange} /> : null}
        {question.answerType === "priority" && question.options ? <PriorityRanking options={question.options} value={Array.isArray(answer) ? answer : []} maxSelections={question.maxSelections} onChange={onChange} /> : null}
        {question.answerType === "text" ? <input type={question.id === "contact_email" ? "email" : "text"} autoComplete={question.id === "contact_email" ? "email" : "off"} value={typeof answer === "string" ? answer : ""} onChange={(event) => onChange(event.target.value)} placeholder={question.placeholder} className="w-full border border-[#cbdcd6] bg-white px-4 py-3.5 text-base text-[#203a32] outline-none focus:border-[#2f806d] focus:ring-2 focus:ring-[#b9dbd0]" /> : null}
        {question.answerType === "number" ? <input type="number" value={typeof answer === "number" ? answer : ""} onChange={(event) => onChange(Number(event.target.value))} className="w-full border border-[#cbdcd6] bg-white px-4 py-3.5 text-base outline-none focus:border-[#2f806d] focus:ring-2 focus:ring-[#b9dbd0]" /> : null}
      </div>
    </fieldset>
  );
}