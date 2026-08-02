import type { AssessmentQuestion } from "@/lib/assessment-schema";

export function UnknownClarificationList({ questions, onEdit }: { questions: AssessmentQuestion[]; onEdit: (questionId: string) => void }) {
  return (
    <section className="mt-8 bg-[#f2f6f4] px-5 py-6 sm:px-7" aria-labelledby="clarification-heading">
      <h3 id="clarification-heading" className="text-lg font-semibold text-[#213b32]">What still needs clarification</h3>
      {questions.length ? (
        <ul className="mt-4 space-y-3">
          {questions.map((question) => <li key={question.id} className="flex items-start justify-between gap-4 text-sm text-[#536a61]"><span>{question.englishLabel}</span><button type="button" onClick={() => onEdit(question.id)} className="shrink-0 font-semibold text-[#246a58] underline underline-offset-4">Review</button></li>)}
        </ul>
      ) : <p className="mt-3 text-sm text-[#536a61]">You have answered every relevant question in this care profile.</p>}
      <p className="mt-4 border-t border-[#d6e2dd] pt-4 text-sm font-semibold text-[#35594d]">OPTIME will not treat unknown as no.</p>
    </section>
  );
}