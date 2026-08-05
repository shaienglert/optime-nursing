import type { AssessmentOption } from "@/lib/assessment-schema";

export function OptionCard({ option, selected, onSelect }: { option: AssessmentOption; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" aria-pressed={selected} onClick={onSelect} className={`group flex min-h-16 w-full items-start gap-4 rounded-lg border-2 px-5 py-4 text-left transition focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-[#1f6f5d] ${selected ? "border-[#2f6f5e] bg-[#e7f1ec] text-[#193d33] shadow-[inset_0_0_0_1px_#2f6f5e]" : "border-[#d6d2c9] bg-white text-[#34312c] hover:border-[#8ca99e]"}`}>
      <span aria-hidden="true" className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded border-2 text-lg font-bold ${selected ? "border-[#2f6f5e] bg-[#2f6f5e] text-white" : "border-[#aaa59c] bg-white text-transparent"}`}>
        ✓
      </span>
      <span>
        <span className="block text-lg font-medium leading-7">{option.label}</span>
        {option.description ? <span className="mt-1 block text-lg leading-7 text-[#575149]">{option.description}</span> : null}
      </span>
    </button>
  );
}