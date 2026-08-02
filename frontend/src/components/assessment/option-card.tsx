import type { AssessmentOption } from "@/lib/assessment-schema";

export function OptionCard({ option, selected, onSelect }: { option: AssessmentOption; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" aria-pressed={selected} onClick={onSelect} className={`min-h-16 w-full border p-4 text-left transition focus-visible:outline-[#2f806d] ${selected ? "border-[#2f806d] bg-[#edf7f3] shadow-[inset_3px_0_0_#2f806d]" : "border-[#d9e4df] bg-white hover:border-[#a8c7bc] hover:bg-[#fbfdfc]"}`}>
      <span className="block text-sm font-semibold text-[#243d35]">{option.label}</span>
      {option.description ? <span className="mt-1 block text-xs leading-5 text-[#647a72]">{option.description}</span> : null}
    </button>
  );
}