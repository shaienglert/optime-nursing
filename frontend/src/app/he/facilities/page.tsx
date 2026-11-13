"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { fetchIsraelFacilities, type IsraelFacilityListItem } from "@/lib/israel-facility";

/** Directory of every Israeli facility home page. */
export default function IsraelFacilityDirectory() {
  const [items, setItems] = useState<IsraelFacilityListItem[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIsraelFacilities().then(setItems).catch((e: Error) => setError(e.message));
  }, []);

  const shown = useMemo(() => {
    const q = query.trim();
    return q ? items.filter((i) => `${i.name} ${i.city ?? ""}`.includes(q)) : items;
  }, [items, query]);

  return (
    <main dir="rtl" lang="he" className="mx-auto max-w-3xl p-6">
      <h1 className="text-3xl font-semibold">מוסדות לגיל השלישי בישראל</h1>
      <input aria-label="חיפוש לפי שם או יישוב" placeholder="חיפוש לפי שם או יישוב" className="mt-4 w-full rounded-xl border p-3" value={query} onChange={(e) => setQuery(e.target.value)} />
      {error ? <p role="alert" className="mt-3">{error}</p> : <p className="mt-3 text-sm text-muted">{shown.length} מוסדות</p>}
      <ul className="mt-3 divide-y">
        {shown.map((item) => (
          <li key={item.canonical_id} className="py-2">
            <Link href={`/he/facility/${item.canonical_id}`} className="font-semibold underline">{item.name}</Link>
            <span className="text-sm text-muted"> · {item.facility_type}{item.city ? ` · ${item.city}` : ""}</span>
          </li>
        ))}
      </ul>
    </main>
  );
}
