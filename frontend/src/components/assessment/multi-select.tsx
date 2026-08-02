import { OptionCard } from "@/components/assessment/option-card";
import { UNKNOWN_FROM_FAMILY, type AssessmentOption } from "@/lib/assessment-schema";

export function MultiSelect({ options, value, maxSelections, onChange }: { options: AssessmentOption[]; value: string[]; maxSelections?: number; onChange: (value: string[]) => void }) {
  const toggle = (optionValue: string) => {
    if (["NONE", UNKNOWN_FROM_FAMILY].includes(optionValue)) {
      onChange(value.includes(optionValue) ? [] : [optionValue]);
      return;
    }
    const withoutExclusive = value.filter((item) => !["NONE", UNKNOWN_FROM_FAMILY].includes(item));
    if (withoutExclusive.includes(optionValue)) onChange(withoutExclusive.filter((item) => item !== optionValue));
    else if (!maxSelections || withoutExclusive.length < maxSelections) onChange([...withoutExclusive, optionValue]);
  };
  return <div className="grid gap-2 sm:grid-cols-2">{options.map((option) => <OptionCard key={option.value} option={option} selected={value.includes(option.value)} onSelect={() => toggle(option.value)} />)}</div>;
}