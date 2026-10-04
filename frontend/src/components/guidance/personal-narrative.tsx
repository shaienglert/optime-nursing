"use client";

import { useEffect, useState } from "react";
import { LiveText } from "./live-text";
import type { QuestionnaireState } from "@/context/questionnaire-context";

type Guidance = { status: string; paragraphs: Array<{ text: string; source_ids: string[] }>; sources: Record<string, string> };
const cache = new Map<string, Guidance>();

export function PersonalNarrative({ state, intakeProfileId, decisionId, facilityId, query, fallback }: {
  state: QuestionnaireState; intakeProfileId?: string; decisionId?: string; facilityId?: string; query?: string; fallback: string[];
}) {
  const request = JSON.stringify({ questionnaire_state: state, natural_language_query: query ?? state.notes ?? "", intake_profile_id: intakeProfileId, decision_id: decisionId, facility_id: facilityId, limit: 50 });
  const [reply, setReply] = useState<{ key: string; data: Guidance } | null>(null);
  const data = cache.get(request) || (reply?.key === request ? reply.data : null);
  const ready = data?.status === "AI_READY";
  const paragraphs = ready ? data.paragraphs.map(p => p.text) : fallback;

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

  return <div className="space-y-4 text-xl leading-9 text-ink">
    {!data && (intakeProfileId || decisionId) ? <p role="status" className="text-base text-forest">I’m bringing the details together for you…</p> : null}
    <LiveText paragraphs={paragraphs} />
    {data?.status === "AI_UNAVAILABLE" ? <p className="text-base text-forest">This explanation is based on your recorded answers and the matching evidence we have.</p> : null}
    {ready ? <details className="text-base"><summary className="cursor-pointer underline underline-offset-4">What this explanation is based on</summary><ul className="mt-3 space-y-2">{[...new Set(data.paragraphs.flatMap(p => p.source_ids))].map(id => <li key={id}>{data.sources[id]}</li>)}</ul></details> : null}
  </div>;
}
