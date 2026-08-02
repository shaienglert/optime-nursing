import type { AssessmentAnswers, AssessmentQuestion } from "@/lib/assessment-schema";

function answerLabel(question: AssessmentQuestion, answer: string | string[] | number | undefined): string {
  if (answer === undefined || answer === "" || (Array.isArray(answer) && answer.length === 0)) return "Not answered";
  const values = Array.isArray(answer) ? answer : [answer];
  return values.map((item) => question.options?.find((option) => option.value === String(item))?.label || String(item)).join(", ");
}

export function ReviewSection({ questions, answers, onEdit }: { questions: AssessmentQuestion[]; answers: AssessmentAnswers; onEdit: (questionId: string) => void }) {
  const categories = [...new Set(questions.map((question) => question.category))];
  return <div className="space-y-5">{categories.map((category) => <section key={category} className="border border-[#d9e4df] bg-white"><div className="border-b border-[#e3ebe8] bg-[#f7faf8] px-4 py-3"><h3 className="text-sm font-bold text-[#2c5146]">{category}</h3></div><dl className="divide-y divide-[#edf1ef]">{questions.filter((question) => question.category === category).map((question) => <div key={question.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-center"><dt className="text-sm text-[#61736d]">{question.englishLabel}</dt><dd className="text-sm font-semibold text-[#243a33]">{answerLabel(question, answers[question.id])}</dd><button type="button" onClick={() => onEdit(question.id)} className="justify-self-start text-xs font-bold text-[#27705f] underline underline-offset-4 sm:justify-self-end">Edit</button></div>)}</dl></section>)}</div>;
}