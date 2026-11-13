"use client";

import { use, useEffect, useState } from "react";

import { fetchIsraelFacility, type IsraelFacilityPage } from "@/lib/israel-facility";
import { photoSrc } from "@/lib/provider-api";

const ACTIVITY_LABELS: Record<string, string> = {
  movies: "סרטים",
  music: "מוזיקה",
  lectures: "הרצאות",
  exercise: "התעמלות",
  gardening: "גינון",
  religious: "פעילות דתית",
  social: "פעילות חברתית",
};

const NOT_PROVIDED = "המוסד עוד לא עדכן";

const NOT_IN_LIST = "לא מופיע ברשימה";

function Row({ label, value, empty = NOT_PROVIDED }: { label: string; value: React.ReactNode; empty?: string }) {
  return (
    <div className="flex gap-3 border-b py-2">
      <dt className="w-44 shrink-0 font-semibold">{label}</dt>
      <dd className="min-w-0 break-words">{value ?? <span className="text-muted">{empty}</span>}</dd>
    </div>
  );
}

const ils = (n: number | null | undefined) => (n == null ? null : `₪${n.toLocaleString("he-IL")}`);
const hostname = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};
const yesNo = (v: "YES" | "NO" | null | undefined) => (v === "YES" ? "כן" : v === "NO" ? "לא" : null);

/** One uniform home page for every Israeli facility in the registry. */
export default function IsraelFacilityHome({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [page, setPage] = useState<IsraelFacilityPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIsraelFacility(id).then(setPage).catch((e: Error) => setError(e.message));
  }, [id]);

  if (error) return <main dir="rtl" lang="he" className="mx-auto max-w-3xl p-6"><p role="alert">{error}</p></main>;
  if (!page) return <main dir="rtl" lang="he" className="mx-auto max-w-3xl p-6"><p>טוען…</p></main>;

  const list = page.from_list;
  const own = page.from_facility;
  const activities = page.activities.filter((a) => a.availability === "YES");

  return (
    <main dir="rtl" lang="he" className="mx-auto max-w-3xl p-6">
      <p className="text-sm text-forest">{list.facility_type}{list.city ? ` · ${list.city}` : ""}</p>
      <h1 className="mt-1 text-3xl font-semibold">{page.name}</h1>
      {page.registration_status === "NOT_REGISTERED" ? (
        <p className="mt-3 rounded-xl border p-3 text-sm">
          המוסד עוד לא השלים את הפרטים שלו ב-OOMNIK. המידע בעמוד הזה מגיע מרשימה ציבורית, ולכן המוסד לא מוצג למשפחות כמתאים עד שיעדכן.
        </p>
      ) : null}

      <section className="mt-6">
        <h2 className="text-xl font-semibold">תמונות</h2>
        {page.photos.length ? (
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {page.photos.map((photo) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={photo.url} src={photoSrc(photo.url)} alt={photo.caption ?? page.name} className="aspect-[4/3] w-full rounded-xl object-cover" />
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-muted">{NOT_PROVIDED}</p>
        )}
      </section>

      <section className="mt-6">
        <h2 className="text-xl font-semibold">שירותים ורישוי</h2>
        <p className="mt-1 text-sm text-muted">מעודכן על ידי המוסד</p>
        <dl className="mt-2">
          <Row label="אוכלוסיות שהמוסד מקבל" value={own?.functional_levels_served.join(", ") || null} />
          <Row label="הסכם קוד עם משרד הבריאות" value={yesNo(own?.moh_code_agreement)} />
          <Row label="רישיון" value={own ? `${own.license_authority}, מספר ${own.license_id}, בתוקף עד ${own.license_expiration_date}` : null} />
          <Row label="מחיר חודשי" value={ils(own?.monthly_price_ils)} />
          <Row label="פיקדון" value={ils(own?.deposit_ils)} />
        </dl>
      </section>

      <section className="mt-6">
        <h2 className="text-xl font-semibold">פעילויות</h2>
        {activities.length ? (
          <ul className="mt-2 flex flex-wrap gap-2">
            {activities.map((a) => <li key={a.category} className="rounded-xl border px-3 py-1">{ACTIVITY_LABELS[a.category] ?? a.category}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-muted">{NOT_PROVIDED}</p>
        )}
      </section>

      <section className="mt-6">
        <h2 className="text-xl font-semibold">פרטים מהרשימה הציבורית</h2>
        <p className="mt-1 text-sm text-muted">מקור: {list.source_name}</p>
        <dl className="mt-2">
          <Row label="יישוב" value={list.city} empty={NOT_IN_LIST} />
          <Row label="מחוז" value={list.district} empty={NOT_IN_LIST} />
          <Row label="מפעיל" value={list.operator_name} empty={NOT_IN_LIST} />
          <Row label="בעלות" value={list.ownership_type} empty={NOT_IN_LIST} />
          <Row label="טלפון" value={list.phone ? <span dir="ltr">{list.phone}</span> : null} empty={NOT_IN_LIST} />
          <Row label="אתר" value={list.website ? <a className="underline" href={list.website} target="_blank" rel="noreferrer" dir="ltr">{hostname(list.website)}</a> : null} empty={NOT_IN_LIST} />
          <Row label="מספר רישום" value={list.license_id} empty={NOT_IN_LIST} />
          <Row label="בהסכם (לפי הרשימה)" value={yesNo(list.moh_code_agreement)} empty={NOT_IN_LIST} />
          <Row label="מחלקות (לפי הרשימה)" value={list.departments.length ? list.departments.join(", ") : null} empty={NOT_IN_LIST} />
          <Row label="יחס לדת" value={list.religion_attitude.length ? list.religion_attitude.join(", ") : null} empty={NOT_IN_LIST} />
        </dl>
      </section>
    </main>
  );
}
