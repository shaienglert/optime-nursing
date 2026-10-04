"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

const subscribeMotion = (notify: () => void) => {
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  media.addEventListener("change", notify);
  return () => media.removeEventListener("change", notify);
};
const motionSnapshot = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const EMPTY_ENDS: number[] = [];

/** Reveals actual wrapped lines, including fallback prose, when they enter view.
 * The complete text stays available to assistive technology; no facts are generated here.
 */
export function LiveText({ paragraphs, className = "" }: { paragraphs: string[]; className?: string }) {
  const textKey = paragraphs.join("\n\n");
  const body = useRef<HTMLDivElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const reducedMotion = useSyncExternalStore(subscribeMotion, motionSnapshot, () => true);
  const [entered, setEntered] = useState(false);
  const [layout, setLayout] = useState<{ key: string; ends: number[] }>({ key: "", ends: [] });
  const [progress, setProgress] = useState<{ key: string; count: number }>({ key: "", count: 0 });
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  useEffect(() => {
    const node = viewport.current;
    if (!node) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { setEntered(true); observer.disconnect(); }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const node = body.current;
    if (!node || reducedMotion) return;
    const measure = () => {
      const top = node.getBoundingClientRect().top;
      const ends: number[] = [];
      for (const paragraph of node.children) {
        const box = paragraph.getBoundingClientRect();
        const style = getComputedStyle(paragraph);
        const lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.65;
        const lines = Math.max(1, Math.round(box.height / lineHeight));
        for (let line = 1; line <= lines; line++) ends.push(box.top - top + Math.min(box.height, line * lineHeight));
      }
      setLayout(current => current.key === textKey && current.ends.length === ends.length && current.ends.every((end, index) => end === ends[index]) ? current : { key: textKey, ends });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    const frame = requestAnimationFrame(measure);
    return () => { cancelAnimationFrame(frame); observer.disconnect(); };
  }, [textKey, reducedMotion]);

  const ends = layout.key === textKey ? layout.ends : EMPTY_ENDS;
  const count = progress.key === textKey ? progress.count : 0;
  const complete = reducedMotion || expandedKey === textKey || (ends.length > 0 && count >= ends.length);
  useEffect(() => {
    if (!entered || complete || !ends.length) return;
    const timer = setInterval(() => setProgress(current => {
      const next = Math.min(ends.length, (current.key === textKey ? current.count : 0) + 1);
      if (next === ends.length) clearInterval(timer);
      return { key: textKey, count: next };
    }), 300);
    return () => clearInterval(timer);
  }, [entered, complete, ends, textKey]);

  return <div ref={viewport} className={className} data-testid="live-text" data-live-complete={complete} style={{ minHeight: "1lh" }}>
    <div style={complete ? undefined : { maxHeight: count ? ends[Math.min(count - 1, ends.length - 1)] : 0, overflow: "hidden" }}>
      <div ref={body} className="space-y-4">{paragraphs.map((text, index) => <p key={index} className="whitespace-pre-wrap break-words">{text}</p>)}</div>
    </div>
    {!complete && entered ? <button type="button" onClick={() => setExpandedKey(textKey)} className="mt-2 min-h-12 text-sm font-medium underline underline-offset-4">Show full text</button> : null}
  </div>;
}
