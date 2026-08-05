"use client";

import { useEffect, useMemo, useState } from "react";

import type { DecisionEngineRecommendation } from "@/lib/api";
import { fetchFacilityDetails } from "@/lib/api";
import { getHomeProgress } from "@/lib/assessment-home-progress";
import {
  ASSESSMENT_PHOTO_LIBRARY,
  DEVELOPMENT_PHOTO_FALLBACK,
  type AssessmentPhotoAsset,
} from "@/lib/assessment-photo-library";
import { ACTIVE_ASSESSMENT_REGION } from "@/lib/assessment-region";
import type { AssessmentAnswers } from "@/lib/assessment-schema";
import { resolveFacilityImage } from "@/lib/facility-experience";

const PHOTO_SESSION_KEY = "optime.assessment.photo.v1";

function selectPhoto(): AssessmentPhotoAsset {
  const preferred = ASSESSMENT_PHOTO_LIBRARY.filter((asset) =>
    asset.marketTags.includes(ACTIVE_ASSESSMENT_REGION.id) || asset.marketTags.includes("desert"),
  );
  const candidates = preferred.length > 0 ? preferred : ASSESSMENT_PHOTO_LIBRARY;
  return candidates[Math.floor(Math.random() * candidates.length)] || ASSESSMENT_PHOTO_LIBRARY[0];
}

function loadSessionPhoto(): AssessmentPhotoAsset {
  try {
    const storedId = window.sessionStorage.getItem(PHOTO_SESSION_KEY);
    const stored = ASSESSMENT_PHOTO_LIBRARY.find((asset) => asset.id === storedId);
    if (stored) return stored;
    const selected = selectPhoto();
    window.sessionStorage.setItem(PHOTO_SESSION_KEY, selected.id);
    return selected;
  } catch {
    return ASSESSMENT_PHOTO_LIBRARY[0];
  }
}

export function AssessmentPhotoEnvironment({ answers, topRecommendation }: {
  answers: AssessmentAnswers;
  topRecommendation?: DecisionEngineRecommendation;
}) {
  const [photo, setPhoto] = useState(ASSESSMENT_PHOTO_LIBRARY[0]);
  const [genericUrl, setGenericUrl] = useState(DEVELOPMENT_PHOTO_FALLBACK);
  const [officialMedia, setOfficialMedia] = useState({ facilityId: "", url: "", ready: false });
  const progress = getHomeProgress(answers);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const selected = loadSessionPhoto();
      setPhoto(selected);
      setGenericUrl(selected.imageUrl);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!topRecommendation?.facility_profile_id) return () => { cancelled = true; };
    void fetchFacilityDetails(String(topRecommendation.facility_profile_id)).then((details) => {
      if (cancelled) return;
      const resolved = resolveFacilityImage(details);
      if (!resolved.isPlaceholder && resolved.url) {
        setOfficialMedia({ facilityId: topRecommendation.canonical_facility_id, url: resolved.url, ready: false });
      }
    }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [topRecommendation]);

  const officialUrl = officialMedia.facilityId === topRecommendation?.canonical_facility_id ? officialMedia.url : "";
  const officialReady = Boolean(officialUrl && officialMedia.ready);
  const officialPending = Boolean(topRecommendation && !officialReady);

  const reveal = useMemo(() => {
    const completed = progress.stages.reduce((sum, stage) => sum + stage.completedAreas, 0);
    const available = progress.stages.reduce((sum, stage) => sum + stage.availableAreas, 0);
    return progress.ready ? 1 : Math.min(0.9, available > 0 ? completed / available : 0);
  }, [progress]);
  const blur = Math.round((1 - reveal) * 14);
  const brightness = 0.62 + reveal * 0.28;
  const saturation = 0.48 + reveal * 0.48;
  const warmth = Math.round(reveal * 9);

  return (
    <div data-assessment-environment data-reveal-ready={progress.ready ? "true" : "false"} className="fixed inset-x-0 bottom-0 top-16 -z-20 overflow-hidden bg-[linear-gradient(135deg,#263c36_0%,#806f55_55%,#c6a96f_100%)]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={genericUrl}
        alt={photo.alt}
        onError={() => setGenericUrl(DEVELOPMENT_PHOTO_FALLBACK)}
        className="assessment-environment-image absolute inset-0 h-full w-full scale-[1.035] object-cover transition-[filter,transform] duration-1000 ease-out motion-reduce:scale-100 motion-reduce:transition-none"
        style={{ filter: `blur(${blur}px) brightness(${brightness}) saturate(${saturation}) sepia(${warmth}%)` }}
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(20,32,28,0.34)_0%,rgba(20,32,28,0.08)_60%,rgba(20,32,28,0.2)_100%)]" />
      {officialUrl ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={officialUrl}
          alt={`${topRecommendation?.facility_name || "Top community"} official community photography`}
          onLoad={() => setOfficialMedia((current) => ({ ...current, ready: true }))}
          onError={() => setOfficialMedia((current) => ({ ...current, url: "", ready: false }))}
          className={`assessment-environment-image absolute inset-0 h-full w-full object-cover transition-opacity duration-300 motion-reduce:transition-none ${officialReady ? "opacity-100" : "opacity-0"}`}
        />
      ) : null}
      {officialPending && topRecommendation ? <p className="absolute bottom-5 right-5 rounded-md bg-[#fffdf8]/90 px-3 py-2 text-xs font-semibold text-[#4f5c56] shadow-sm backdrop-blur-sm">Official community photography is currently being verified.</p> : null}
      <p className="sr-only">Development image source: Pexels photo {photo.id}. This generic image does not depict a recommended facility.</p>
    </div>
  );
}
