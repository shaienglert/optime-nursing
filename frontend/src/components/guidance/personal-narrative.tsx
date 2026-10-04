"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import type { QuestionnaireState } from "@/context/questionnaire-context";

type Guidance = { status: string; paragraphs: Array<{ text: string; source_ids: string[] }>; sources: Record<string, string> };
const cache = new Map<string, Guidance>();
const subscribeMotion = (callback: () => void) => {
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
};
const reducedMotionSnapshot = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function PersonalNarrative({ state, intakeProfileId, decisionId, facilityId, query, fallback }: {
  state: QuestionnaireState; intakeProfileId?: string; decisionId?: string; facilityId?: string; query?: string; fallback: string[];
}) {
  const request = JSON.stringify({ questionnaire_state: state, natural_language_query: query ?? state.notes ?? "", intake_profile_id: intakeProfileId, decision_id: decisionId, facility_id: facilityId, limit: 50 });
  const [reply, setReply] = useState<{ key: string; data: Guidance } | null>(null);
  const [visible, setVisible] = useState<{ key: string; count: number }>({ key: "", count: 0 });
  const data = cache.get(request) || (reply?.key === request ? reply.data : null);
  const reducedMotion = useSyncExternalStore(subscribeMotion, reducedMotionSnapshot, () => true);
  const ready = data?.status === "AI_READY";
  const fullText = (ready ? data.paragraphs.map(p => p.text) : fallback).join("\n\n");

  useEffect(() => {
    if (!intakeProfileId && !decisionId) return;
    let active = true;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 24000);
    const saved = cache.get(request);
    if (saved) { window.clearTimeout(timer); return; }
    void fetch("/api/backend/api/client-guidance", { method: "POST", headers: { "Content-Type": "application/json" }, body: request, signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error("Guidance unavailable"); return response.json() as Promise<Guidance>; })
      .then(value => { if (active) { if (value.status === "AI_READY") { if (cache.size >= 30) cache.clear(); cache.set(request, value); } setReply({ key: request, data: value }); } })
      .catch(() => { if (active) setReply({ key: request, data: { status: "AI_UNAVAILABLE", paragraphs: [], sources: {} } }); })
      .finally(() => window.clearTimeout(timer));
    return () => { active = false; window.clearTimeout(timer); controller.abort(); };
  }, [request, intakeProfileId, decisionId]);

  useEffect(() => {
    if (!ready || reducedMotion) return;
    const timer = window.setInterval(() => setVisible(current => {
      const count = Math.min(fullText.length, (current.key === fullText ? current.count : 0) + 32);
      if (count === fullText.length) window.clearInterval(timer);
      return { key: fullText, count };
    }), 24);
    return () => window.clearInterval(timer);
  }, [fullText, ready, reducedMotion]);

  const displayed = ready && !reducedMotion ? fullText.slice(0, visible.key === fullText ? visible.count : 0) : fullText;
  return <div className="space-y-4 text-xl leading-9 text-[#302940]">
    {!data && (intakeProfileId || decisionId) ? <p role="status" className="text-base text-[#675088]">I’m bringing the details together for you…</p> : null}
    <div aria-hidden={ready && displayed !== fullText} className="space-y-4">{displayed.split("\n\n").map((text, index) => <p key={index} className="whitespace-pre-wrap break-words">{text}</p>)}</div>
    {ready && displayed !== fullText ? <p className="sr-only">{fullText}</p> : null}
    {data?.status === "AI_UNAVAILABLE" ? <p className="text-base text-[#675088]">This explanation is based on your recorded answers and the matching evidence we have.</p> : null}
    {ready ? <details className="text-base"><summary className="cursor-pointer underline underline-offset-4">What this explanation is based on</summary><ul className="mt-3 space-y-2">{[...new Set(data.paragraphs.flatMap(p => p.source_ids))].map(id => <li key={id}>{data.sources[id]}</li>)}</ul></details> : null}
  </div>;
}
