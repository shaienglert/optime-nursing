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
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.08em] text-[#667a73]">Choose up to {maxSelections}</p><div className="space-y-2">{options.filter((option) => !value.includes(option.value)).map((option) => <button key={option.value} type="button" disabled={value.length >= maxSelections} onClick={() => onChange([...value, option.value])} className="w-full border border-[#d9e4df] bg-white px-4 py-3 text-left text-sm font-medium hover:border-[#9fc1b5] disabled:cursor-not-allowed disabled:opacity-45">{option.label}</button>)}</div></div>
      <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.08em] text-[#667a73]">Your ranked priorities</p><ol className="space-y-2">{value.map((item, index) => <li key={item} className="flex min-h-14 items-center gap-3 border border-[#b7d2c9] bg-[#edf7f3] px-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#2f806d] text-xs font-bold text-white">{index + 1}</span><span className="flex-1 text-sm font-semibold">{optionByValue.get(item)?.label || item}</span><button type="button" aria-label={`Move ${optionByValue.get(item)?.label} up`} title="Move up" onClick={() => move(index, -1)} disabled={index === 0} className="h-8 w-8 text-lg disabled:opacity-25">↑</button><button type="button" aria-label={`Move ${optionByValue.get(item)?.label} down`} title="Move down" onClick={() => move(index, 1)} disabled={index === value.length - 1} className="h-8 w-8 text-lg disabled:opacity-25">↓</button><button type="button" aria-label={`Remove ${optionByValue.get(item)?.label}`} title="Remove" onClick={() => onChange(value.filter((valueItem) => valueItem !== item))} className="h-8 w-8 text-sm">×</button></li>)}</ol>{value.length === 0 ? <p className="border border-dashed border-[#cadbd5] p-4 text-sm text-[#687c75]">Your first choice will have the most influence.</p> : null}</div>
    </div>
  );
}