"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "oomnik-font-scale";
const SCALES = ["normal", "large", "x-large"] as const;
type FontScale = (typeof SCALES)[number];

export function FontSizeControl() {
  const [scale, setScale] = useState<FontScale>("normal");
  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY) as FontScale | null;
    const next = saved && SCALES.includes(saved) ? saved : "normal";
    setScale(next);
    document.documentElement.dataset.fontScale = next;
  }, []);
  function update(next: FontScale) {
    setScale(next);
    document.documentElement.dataset.fontScale = next;
    window.localStorage.setItem(STORAGE_KEY, next);
  }
  return <div className="inline-flex items-center rounded-full border border-[#d9e4df] bg-white p-1 shadow-sm" aria-label="Text size">
    <button type="button" onClick={() => update("normal")} aria-pressed={scale === "normal"} className="min-h-10 min-w-10 rounded-full px-2 text-sm font-semibold">A−</button>
    <button type="button" onClick={() => update("large")} aria-pressed={scale === "large"} className="min-h-10 min-w-10 rounded-full px-2 text-base font-semibold">A</button>
    <button type="button" onClick={() => update("x-large")} aria-pressed={scale === "x-large"} className="min-h-10 min-w-10 rounded-full px-2 text-lg font-semibold">A+</button>
  </div>;
}
