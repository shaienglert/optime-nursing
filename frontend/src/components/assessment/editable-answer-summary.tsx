import { ASSESSMENT_SECTIONS, getAssessmentSection } from "@/lib/assessment-conversation";
import { UNKNOWN_FROM_FAMILY, type AssessmentAnswers, type AssessmentQuestion } from "@/lib/assessment-schema";

function answerLabel(question: AssessmentQuestion, answers: AssessmentAnswers): string {
  const answer = answers[question.id];
  const values = Array.isArray(answer) ? answer : answer === undefined ? [] : [answer];
  if (!values.length) return "Not answered";
  return values.map((value) => value === UNKNOWN_FROM_FAMILY ? "Not sure" : question.options?.find((option) => option.value === value)?.label || String(value)).join(", ");
}

export function EditableAnswerSummary({ questions, answers, onEdit }: { questions: AssessmentQuestion[]; answers: AssessmentAnswers; onEdit: (questionId: string) => void }) {
  return (
    <div className="divide-y divide-[#dfe8e4] border-y border-[#dfe8e4]">
      {ASSESSMENT_SECTIONS.filter((section) => section.id !== "summary").map((section) => {
        const sectionQuestions = questions.filter((question) => getAssessmentSection(question).id === section.id);
        if (!sectionQuestions.length) return null;
        return (
          <section key={section.id} className="py-6">
            <h3 className="text-sm font-semibold text-[#294c41]">{section.label}</h3>
            <dl className="mt-3 space-y-3">
              {sectionQuestions.map((question) => (
                <div key={question.id} className="grid gap-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-start sm:gap-5">
                  <dt className="text-sm text-[#64776f]">{question.englishLabel}</dt>
                  <dd className="text-sm font-medium text-[#223a32]">{answerLabel(question, answers)}</dd>
                  <button type="button" onClick={() => onEdit(question.id)} className="justify-self-start text-xs font-semibold text-[#246a58] underline decoration-[#9fc5b8] underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#246a58] sm:justify-self-end">Edit</button>
                </div>
              ))}
            </dl>
          </section>
        );
      })}
    </div>
  );
}