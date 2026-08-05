"use client";

import type { ReactNode } from "react";
import { useState } from "react";

export function PagedOptionList<T extends { value: string }>({ options, children }: {
  options: T[];
  selectedValues?: string[];
  children: (option: T) => ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  const visibleOptions = expanded ? options : options.slice(0, 10);
  return (
    <div>
      <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2">
        {visibleOptions.map((option) => children(option))}
      </div>
      {!expanded && options.length > 10 ? (
        <button type="button" onClick={() => setExpanded(true)} className="mt-5 min-h-12 border-b-2 border-[#2f6f5e] text-lg font-semibold text-[#2f6f5e] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#2f6f5e]">
          See {options.length - 10} more choices
        </button>
      ) : null}
    </div>
  );
}