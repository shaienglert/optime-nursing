"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { IsraelPhotoManager } from "@/components/provider/israel-photo-manager";
import { providerSessionSnapshot, subscribeProviderSession, type ProviderSession } from "@/lib/provider-session";
import { fetchIsraelRegistration, saveIsraelRegistration, type IsraelFunctionalLevel, type IsraelRegistration } from "@/lib/provider-api";

const LEVELS: { value: IsraelFunctionalLevel; label: string }[] = [
  { value: "INDEPENDENT", label: "עצמאיים" },
  { value: "FRAIL", label: "תשושים" },
  { value: "NURSING", label: "סיעודיים" },
  { value: "COGNITIVE_FRAIL", label: "תשושי נפש" },
];

/**
 * Israeli facility registration. What the facility fills in here is the only data
 * OOMNIK uses to match it to families in Israel (owner decision, 2026-11-13).
 */
export default function IsraelRegistrationPage({ params }: { params: Promise<{ facilityId: string }> }) {
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

  const [levels, setLevels] = useState<IsraelFunctionalLevel[]>([]);
  const [agreement, setAgreement] = useState<"YES" | "NO" | "">("");
  const [authority, setAuthority] = useState<"MINISTRY_OF_HEALTH" | "MINISTRY_OF_WELFARE" | "">("");
  const [licenseId, setLicenseId] = useState("");
  const [expires, setExpires] = useState("");
  const [monthly, setMonthly] = useState("");
  const [deposit, setDeposit] = useState("");
  const [status, setStatus] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [hasSaved, setHasSaved] = useState(false);

  // "Confirm the existing information": start from what the facility already saved.
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    fetchIsraelRegistration(facilityId)
      .then(({ registration: saved }) => {
        if (cancelled || !saved) return;
        setLevels(saved.functional_levels_served);
        setAgreement(saved.moh_code_agreement);
        setAuthority(saved.license_authority);
        setLicenseId(saved.license_id);
        setExpires(saved.license_expiration_date);
        setMonthly(saved.monthly_price_ils != null ? String(saved.monthly_price_ils) : "");
        setDeposit(saved.deposit_ils != null ? String(saved.deposit_ils) : "");
        setHasSaved(true);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [session, facilityId]);

  const toggle = (level: IsraelFunctionalLevel) =>
    setLevels((current) => (current.includes(level) ? current.filter((l) => l !== level) : [...current, level]));

  const complete = levels.length > 0 && agreement && authority && licenseId.trim() && expires;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!userId || !complete) return;
    const registration: IsraelRegistration = {
      functional_levels_served: levels,
      moh_code_agreement: agreement as "YES" | "NO",
      license_id: licenseId.trim(),
      license_authority: authority as IsraelRegistration["license_authority"],
      license_expiration_date: expires,
      monthly_price_ils: monthly ? Number(monthly) : null,
      deposit_ils: deposit ? Number(deposit) : null,
    };
    setSaving(true);
    setStatus(null);
    try {
      const result = await saveIsraelRegistration(facilityId, userId, registration);
      setStatus({ kind: "ok", text: result.changed ? "הפרטים נשמרו. מעכשיו OOMNIK יתאים את המוסד למשפחות לפיהם." : "הפרטים אושרו ללא שינוי." });
    } catch (error) {
      setStatus({ kind: "error", text: error instanceof Error ? error.message : "השמירה נכשלה." });
    } finally {
      setSaving(false);
    }
  }

  const field = "mt-1 w-full rounded-xl border p-2";

  return (
    <main dir="rtl" lang="he" className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">{session ? session.name : "הפורטל של המוסד"}</h1>
      <p className="mt-2 text-sm">
        ההתאמה למשפחות נעשית רק לפי הפרטים שתמלאו כאן. מוסד שלא מילא פרטים לא יוצג כמתאים, וגם לא ייפסל.
      </p>
      {session ? (
        <p className="mt-2 text-sm">
          <Link className="underline" href={`/he/facility/${encodeURIComponent(session.canonical_id)}`}>לצפייה בדף הבית של המוסד</Link>
        </p>
      ) : (
        <p role="alert" className="mt-4 rounded-xl border p-3 text-sm">כדי לערוך, יש להיכנס דרך הקישור האישי שהמוסד קיבל מ-OOMNIK.</p>
      )}
      {hasSaved ? (
        <p className="mt-4 rounded-xl border p-3 text-sm">אלה הפרטים ששמרתם. אם הכול נכון, לחצו על &quot;אישור הפרטים&quot;. אם משהו השתנה, תקנו ושמרו.</p>
      ) : null}

      <form onSubmit={submit} className="mt-6 space-y-6">
        <fieldset>
          <legend className="font-medium">אילו אוכלוסיות המוסד מקבל?</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {LEVELS.map((level) => (
              <label key={level.value} className="flex items-center gap-2 rounded-xl border px-3 py-2">
                <input type="checkbox" checked={levels.includes(level.value)} onChange={() => toggle(level.value)} />
                {level.label}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="font-medium">האם למוסד יש הסכם עם משרד הבריאות לקבלת מטופלים בקוד?</legend>
          <div className="mt-2 flex gap-3">
            {(["YES", "NO"] as const).map((value) => (
              <label key={value} className="flex items-center gap-2 rounded-xl border px-3 py-2">
                <input type="radio" name="agreement" checked={agreement === value} onChange={() => setAgreement(value)} />
                {value === "YES" ? "כן" : "לא"}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="font-medium">רישיון</legend>
          <label className="block text-sm">
            הגוף המרשה
            <select className={field} value={authority} onChange={(e) => setAuthority(e.target.value as typeof authority)}>
              <option value="" disabled>בחרו</option>
              <option value="MINISTRY_OF_HEALTH">משרד הבריאות</option>
              <option value="MINISTRY_OF_WELFARE">משרד הרווחה</option>
            </select>
          </label>
          <label className="block text-sm">
            מספר רישיון
            <input className={field} value={licenseId} onChange={(e) => setLicenseId(e.target.value)} dir="ltr" />
          </label>
          <label className="block text-sm">
            תוקף הרישיון עד
            <input type="date" className={field} value={expires} onChange={(e) => setExpires(e.target.value)} dir="ltr" />
          </label>
        </fieldset>

        <fieldset className="space-y-3">
          <legend className="font-medium">מחירים (לא חובה)</legend>
          <label className="block text-sm">
            מחיר חודשי ב-₪
            <input type="number" min={0} className={field} value={monthly} onChange={(e) => setMonthly(e.target.value)} dir="ltr" />
          </label>
          <label className="block text-sm">
            פיקדון ב-₪ (דיור מוגן)
            <input type="number" min={0} className={field} value={deposit} onChange={(e) => setDeposit(e.target.value)} dir="ltr" />
          </label>
        </fieldset>

        <button type="submit" disabled={!userId || !complete || saving} className="rounded-xl px-4 py-2 font-medium" style={{ backgroundColor: "var(--primary)", color: "var(--primary-contrast)" }}>
          {saving ? "שומר…" : hasSaved ? "אישור הפרטים" : "שמירה"}
        </button>
        {status ? (
          <p role={status.kind === "error" ? "alert" : "status"} className="text-sm">{status.text}</p>
        ) : null}
      </form>

      <IsraelPhotoManager facilityId={facilityId} userId={userId} />
    </main>
  );
}
