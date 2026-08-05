import { PagedOptionList } from "@/components/assessment/paged-option-list";
import { UNKNOWN_FROM_FAMILY } from "@/lib/assessment-schema";
import type { AssessmentOption } from "@/lib/assessment-schema";

export function PriorityRanking({ options, value, maxSelections = 5, onChange }: { options: AssessmentOption[]; value: string[]; maxSelections?: number; onChange: (value: string[]) => void }) {
  const optionByValue = new Map(options.map((option) => [option.value, option]));
  const move = (index: number, offset: number) => {
    const target = index + offset;
    if (target < 0 || target >= value.length) return;
    const next = [...value];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };
  const knownValues = value.filter((item) => item !== UNKNOWN_FROM_FAMILY);
  return (
    <div className="space-y-5">
      <div><p className="mb-3 text-lg text-[#526a62]">Choose up to {maxSelections} in the order that matters most.</p><PagedOptionList options={options.filter((option) => !knownValues.includes(option.value))} selectedValues={knownValues}>{(option) => <button key={option.value} type="button" disabled={knownValues.length >= maxSelections} onClick={() => onChange([...knownValues, option.value])} className="min-h-14 rounded-lg border-2 border-[#c8d9d3] bg-white px-5 py-3 text-left text-lg font-semibold text-[#183d32] hover:border-[#6d9d8d] disabled:cursor-not-allowed disabled:opacity-45">{option.label}</button>}</PagedOptionList></div>
      <button type="button" onClick={() => onChange([UNKNOWN_FROM_FAMILY])} className="min-h-14 w-full rounded-lg border-2 border-[#c8d9d3] bg-white px-5 py-3 text-left text-lg font-semibold text-[#183d32]">Not sure yet</button>
      {knownValues.length ? <div><p className="mb-2 text-lg font-semibold text-[#36574c]">Most important first</p><ol className="space-y-2">{knownValues.map((item, index) => <li key={item} className="flex min-h-14 items-center gap-2 rounded-lg bg-[#e9f4ef] px-3 ring-2 ring-[#bed6cd]"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#2f806d] text-lg font-bold text-white">{index + 1}</span><span className="flex-1 text-lg font-semibold">{optionByValue.get(item)?.label || item}</span><button type="button" aria-label={`Move ${optionByValue.get(item)?.label} up`} title="Move up" onClick={() => move(index, -1)} disabled={index === 0} className="h-11 w-11 text-xl disabled:opacity-25">↑</button><button type="button" aria-label={`Move ${optionByValue.get(item)?.label} down`} title="Move down" onClick={() => move(index, 1)} disabled={index === knownValues.length - 1} className="h-11 w-11 text-xl disabled:opacity-25">↓</button><button type="button" aria-label={`Remove ${optionByValue.get(item)?.label}`} title="Remove" onClick={() => onChange(knownValues.filter((valueItem) => valueItem !== item))} className="h-11 w-11 text-xl">×</button></li>)}</ol></div> : null}
    </div>
  );
}