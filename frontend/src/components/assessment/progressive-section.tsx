import type { ReactNode } from "react";

export function ProgressiveSection({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="pt-10 first:pt-8" aria-labelledby={`section-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
      <div className="mb-6 flex items-center gap-4">
        <h2 id={`section-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} className="shrink-0 text-xs font-bold uppercase tracking-[0.12em] text-[#397261]">{label}</h2>
        <div className="h-px flex-1 bg-[#dce7e2]" />
      </div>
      <div className="space-y-8">{children}</div>
    </section>
  );
}