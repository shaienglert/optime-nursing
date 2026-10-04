"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "oomnik-font-scale";
const SCALES = ["normal", "large", "x-large"] as const;
type FontScale = (typeof SCALES)[number];

function readScale(): FontScale {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return SCALES.includes(stored as FontScale) ? (stored as FontScale) : "normal";
  } catch {
    return "normal";
  }
}

export function FontSizeControl() {
  const [scale, setScale] = useState<FontScale>(() =>
    typeof window === "undefined" ? "normal" : readScale(),
  );

  useEffect(() => {
    document.documentElement.dataset.fontScale = scale;
  }, [scale]);

  function update(next: FontScale) {
    setScale(next);
    document.documentElement.dataset.fontScale = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Preference storage is optional.
    }
  }

  return (
    <div className="inline-flex items-center rounded-xl border border-[#e4ded4] bg-white p-1 shadow-sm" aria-label="Text size">
      <button type="button" onClick={() => update("normal")} aria-pressed={scale === "normal"} className={`min-h-12 min-w-12 rounded-xl px-2 text-sm font-semibold ${scale === "normal" ? "bg-[#f1f0e8] text-[#1a1d20]" : "text-[#284b38] hover:bg-[#f1f0e8]"}`}>A−</button>
      <button type="button" onClick={() => update("large")} aria-pressed={scale === "large"} className={`min-h-12 min-w-12 rounded-xl px-2 text-base font-semibold ${scale === "large" ? "bg-[#f1f0e8] text-[#1a1d20]" : "text-[#284b38] hover:bg-[#f1f0e8]"}`}>A</button>
      <button type="button" onClick={() => update("x-large")} aria-pressed={scale === "x-large"} className={`min-h-12 min-w-12 rounded-xl px-2 text-lg font-semibold ${scale === "x-large" ? "bg-[#f1f0e8] text-[#1a1d20]" : "text-[#284b38] hover:bg-[#f1f0e8]"}`}>A+</button>
    </div>
  );
}
