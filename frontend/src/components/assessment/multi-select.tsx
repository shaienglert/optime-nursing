import { OptionCard } from "@/components/assessment/option-card";
import { PagedOptionList } from "@/components/assessment/paged-option-list";
import { UNKNOWN_FROM_FAMILY, type AssessmentOption } from "@/lib/assessment-schema";

const EXCLUSIVE_VALUES = new Set(["NONE", "INDEPENDENT", "LAS_VEGAS_VALLEY", UNKNOWN_FROM_FAMILY]);

export function MultiSelect({ options, value, maxSelections, onChange }: { options: AssessmentOption[]; value: string[]; maxSelections?: number; onChange: (value: string[]) => void }) {
  const toggle = (optionValue: string) => {
    if (EXCLUSIVE_VALUES.has(optionValue)) {
      onChange(value.includes(optionValue) ? [] : [optionValue]);
      return;
    }
    const withoutExclusive = value.filter((item) => !EXCLUSIVE_VALUES.has(item));
    if (withoutExclusive.includes(optionValue)) onChange(withoutExclusive.filter((item) => item !== optionValue));
    else if (!maxSelections || withoutExclusive.length < maxSelections) onChange([...withoutExclusive, optionValue]);
  };
  return <PagedOptionList options={options} selectedValues={value}>{(option) => <OptionCard key={option.value} option={option} selected={value.includes(option.value)} onSelect={() => toggle(option.value)} />}</PagedOptionList>;
}