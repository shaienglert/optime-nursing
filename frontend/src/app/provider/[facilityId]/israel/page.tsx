"use client";

import Link from "next/link";
import { use, useMemo, useSyncExternalStore } from "react";

import { IsraelPhotoManager } from "@/components/provider/israel-photo-manager";
import { IsraelQuestionnaire } from "@/components/provider/israel-questionnaire";
import { providerSessionSnapshot, subscribeProviderSession, type ProviderSession } from "@/lib/provider-session";

/**
 * The Israeli facility portal. What the facility fills in here is the only data
 * OOMNIK uses to match it to families in Israel (owner decision, 2026-11-13).
 */
export default function IsraelFacilityPortalPage({ params }: { params: Promise<{ facilityId: string }> }) {
  const { facilityId: rawId } = use(params);
  const facilityId = Number(rawId);
  const rawSession = useSyncExternalStore(subscribeProviderSession, providerSessionSnapshot, () => null);
  const session = useMemo<ProviderSession | null>(() => {
    try {
      const parsed = rawSession ? (JSON.parse(rawSession) as ProviderSession) : null;
      return parsed && parsed.facility_id === facilityId ? parsed : null;
    } catch {
      return null;
    }
  }, [rawSession, facilityId]);
  const userId = session?.user_id ?? null;

  return (
    <main dir="rtl" lang="he" className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">{session ? session.name : "הפורטל של המוסד"}</h1>
      <p className="mt-2 text-sm">
        ההתאמה למשפחות נעשית רק לפי הפרטים שתמלאו כאן. שאלה שלא עניתם עליה נחשבת &quot;לא ידוע&quot;, ולא פוסלת את המוסד.
        שאלות עם * הן חובה.
      </p>
      {session ? (
        <p className="mt-2 text-sm">
          <Link className="underline" href={`/he/facility/${encodeURIComponent(session.canonical_id)}`}>לצפייה בדף הבית של המוסד</Link>
        </p>
      ) : (
        <p role="alert" className="mt-4 rounded-xl border p-3 text-sm">כדי לערוך, יש להיכנס דרך הקישור האישי שהמוסד קיבל מ-OOMNIK.</p>
      )}

      <IsraelQuestionnaire facilityId={facilityId} userId={userId} />
      <IsraelPhotoManager facilityId={facilityId} userId={userId} />
    </main>
  );
}
