"use client";

import { useEffect, useRef } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { loadFavoriteFacilities } from "@/lib/search-session";

type ContinuityState = {
  phase: "COMPARE" | "RECOMMEND" | "FOLLOW_UP";
  lastEvent: "RESULTS_VIEWED" | "SHORTLIST_UPDATED" | "COMPARE_OPENED" | "COMPARE_RETURNED";
  shortlistFacilityIds: string[];
  comparedFacilityIds: string[];
  updatedAt: string;
};

function sameIds(a: string[], b: string[]) {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

export function ProcessContinuityBridge({ children }: { children: React.ReactNode }) {
  const { state, setState } = useQuestionnaire();
  const stateRef = useRef(state);
  const signatureRef = useRef("");

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    const sync = () => {
      const pathname = window.location.pathname;
      if (pathname !== "/results" && pathname !== "/compare") return;

      const params = new URLSearchParams(window.location.search);
      const shortlist = [...loadFavoriteFacilities()].sort();
      const compared = (params.get("facilities") || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean)
        .sort();
      const previous = ((stateRef.current as unknown as Record<string, unknown>).aiProcessContinuity || {}) as Partial<ContinuityState>;

      let event: ContinuityState["lastEvent"] = pathname === "/compare" ? "COMPARE_OPENED" : "RESULTS_VIEWED";
      let phase: ContinuityState["phase"] = pathname === "/compare" ? "COMPARE" : "RECOMMEND";
      if (pathname === "/results" && shortlist.length && !sameIds(shortlist, previous.shortlistFacilityIds || [])) {
        event = "SHORTLIST_UPDATED";
        phase = "COMPARE";
      } else if (pathname === "/results" && previous.lastEvent === "COMPARE_OPENED") {
        event = "COMPARE_RETURNED";
        phase = "FOLLOW_UP";
      }

      const effectiveCompared = pathname === "/compare" ? compared : (previous.comparedFacilityIds || []);
      const signature = JSON.stringify({ pathname, event, phase, shortlist, compared: effectiveCompared });
      if (signature === signatureRef.current) return;
      signatureRef.current = signature;

      const nextContinuity: ContinuityState = {
        phase,
        lastEvent: event,
        shortlistFacilityIds: shortlist,
        comparedFacilityIds: effectiveCompared,
        updatedAt: new Date().toISOString(),
      };
      const next = {
        ...(stateRef.current as unknown as Record<string, unknown>),
        aiProcessContinuity: nextContinuity,
      } as unknown as typeof stateRef.current;
      stateRef.current = next;
      setState(next);
    };

    sync();
    const timer = window.setInterval(sync, 500);
    return () => window.clearInterval(timer);
  }, [setState]);

  return <>{children}</>;
}
