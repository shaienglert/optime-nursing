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
    <div className="inline-flex items-center rounded-full border border-[#d9e4df] bg-white p-1 shadow-sm" aria-label="Text size">
      <button type="button" onClick={() => update("normal")} aria-pressed={scale === "normal"} className={`min-h-10 min-w-10 rounded-full px-2 text-sm font-semibold ${scale === "normal" ? "bg-[#eaf5f0] text-[#1e4f43]" : "text-[#52645d] hover:bg-[#f4f8f6]"}`}>A−</button>
      <button type="button" onClick={() => update("large")} aria-pressed={scale === "large"} className={`min-h-10 min-w-10 rounded-full px-2 text-base font-semibold ${scale === "large" ? "bg-[#eaf5f0] text-[#1e4f43]" : "text-[#52645d] hover:bg-[#f4f8f6]"}`}>A</button>
      <button type="button" onClick={() => update("x-large")} aria-pressed={scale === "x-large"} className={`min-h-10 min-w-10 rounded-full px-2 text-lg font-semibold ${scale === "x-large" ? "bg-[#eaf5f0] text-[#1e4f43]" : "text-[#52645d] hover:bg-[#f4f8f6]"}`}>A+</button>
    </div>
  );
}
