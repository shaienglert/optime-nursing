"use client";

import Link from "next/link";
import { FormEvent, useRef, useState } from "react";

type Criterion = { parameter: string; priority: number | null; value: unknown; source: string | null; role: string; evidence_state?: string; direction?: string };
type RankedRow = {
  display_position: number; rank_display: string | null; facility_id: string; facility_name: string;
  tie_status: string; must_status: string; must_pass: string[]; must_unknown: string[];
  nice_match: string[]; nice_unknown: string[]; budget_exception: boolean | null;
  budget_variance_pct: number | null; snapshot_status: string; criteria: Criterion[];
  comparison_vs_next: { deciding_dimension?: string; why_ranked_above?: string; remaining_unknown?: string[] } | null;
};
type SearchSummary = { id: string; created_at_epoch: number; returned_count: number; total_candidates_scored: number; top_count: number };
type Audit = SearchSummary & { rows: RankedRow[]; pipeline_trace: unknown };

const labels: Record<string, string> = {
  strict_budget_before_expansion: "התאמה לתקציב לפני הרחבה", community_preference_evidence: "ראיות להעדפת קהילה",
  community_preference_fit: "התאמה לסוג הקהילה", must_gate: "תנאי חובה", care_setting_fit: "התאמה למסגרת הטיפול",
  verified_preference_matches: "העדפות מאומתות שתואמות", verified_preference_mismatches: "העדפות עם אי־התאמה מאומתת",
  community_environment_evidence: "ראיות לסביבת המגורים", community_environment_fit: "התאמה לסביבה המבוקשת",
  nearby_comparison_scope: "היקף השוואת הסביבה", requested_nearby_fit: "התאמה למקומות בקרבת המוסד",
  requested_nearby_distance: "מרחק מהמקומות המבוקשים", alis_disciplinary_action: "הליכים משמעתיים",
  alis_latest_grade: "ציון רגולטורי אחרון", alis_grade_counts: "היסטוריית ציונים", inspection_rating: "ציון ביקורת",
  deficiency_count: "מספר ליקויים", total_nurse_hours_per_resident_day: "שעות סיעוד לדייר", rn_hours_per_resident_day: "שעות אחות מוסמכת",
  staffing_turnover: "תחלופת עובדים", public_rating: "דירוג ציבורי", public_review_count: "מספר ביקורות",
  relevant_evidence_known_count: "ראיות רלוונטיות למקרה", true_tie: "תיקו אמיתי",
};
const name = (key: string) => labels[key] || key.replaceAll("_", " ");
const value = (v: unknown): string => v === null || v === undefined ? "לא ידוע" : typeof v === "object" ? JSON.stringify(v) : String(v);
const when = (epoch: number) => new Date(epoch * 1000).toLocaleString("he-IL");
const cell = "border-b border-line px-3 py-3 text-right align-top";

export default function SearchRankingPage() {
  const [token, setToken] = useState("");
  const [searches, setSearches] = useState<SearchSummary[]>([]);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [offset, setOffset] = useState(0);
  const [more, setMore] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef(0);

  async function load(pageOffset: number, auditId?: string) {
    const current = ++requestId.current;
    setBusy(true); setError(""); setAudit(null);
    // Clear protected data before checking a new credential, including failures.
    if (!auditId) { setSearches([]); setLoaded(false); }
    try {
      const suffix = auditId ? `/${encodeURIComponent(auditId)}` : `?limit=25&offset=${pageOffset}`;
      const response = await fetch(`/api/backend/api/admin/search-ranking-audits${suffix}`, {
        headers: { "x-admin-token": token.trim() }, cache: "no-store",
      });
      if (!response.ok) throw new Error(response.status === 401 ? "קוד הגישה אינו תקין או חסר." : "לא ניתן לטעון את הבדיקה. נסו שוב.");
      const data = await response.json();
      if (current !== requestId.current) return;
      if (auditId) setAudit(data);
      else { setSearches(data.items); setMore(data.has_more); setOffset(pageOffset); setLoaded(true); }
    } catch (e) {
      if (current === requestId.current) setError(e instanceof Error ? e.message : "שגיאה בטעינה");
    } finally { if (current === requestId.current) setBusy(false); }
  }

  function submit(e: FormEvent) { e.preventDefault(); void load(0); }

  return <main dir="rtl" lang="he" className="min-h-screen bg-canvas px-4 py-8 text-ink sm:px-8">
    <div className="mx-auto max-w-7xl space-y-6">
      <Link href="/admin" className="text-sm underline">חזרה לאדמין</Link>
      <header><p className="text-sm text-forest">בקרת חיפושים</p><h1 className="mt-2 text-3xl font-semibold">למה נבחרו עשרת המקומות הראשונים?</h1>
        <p className="mt-3 text-muted">הסדר והראיות נשמרים בזמן החיפוש. המנוע משתמש בסדר עדיפויות, ולכן אין משקל באחוזים או ציון כולל שמסביר את הדירוג.</p>
      </header>
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-2xl border border-line p-4">
        <label className="text-sm">קוד גישת אדמין<input type="password" autoComplete="off" value={token} required
          onChange={e => { ++requestId.current; setToken(e.target.value); setAudit(null); setSearches([]); setLoaded(false); setBusy(false); setError(""); }}
          className="mt-1 block rounded-lg border border-line bg-surface p-2" /></label>
        <button disabled={busy || !token.trim()} className="rounded-lg bg-forest px-4 py-2 text-white disabled:opacity-50">{busy ? "טוען…" : "טען חיפושים"}</button>
      </form>
      {error ? <p role="alert" className="rounded-xl border border-red-300 p-3 text-red-700">{error}</p> : null}
      {loaded ? <section className="space-y-3" aria-label="היסטוריית חיפושים">
        <label className="block text-sm">בחירת חיפוש<select value={audit?.id || ""} disabled={busy} onChange={e => { if (e.target.value) void load(offset, e.target.value); }} className="mt-1 block w-full rounded-lg border border-line bg-surface p-3">
          <option value="">בחרו חיפוש לבדיקה</option>{searches.map(s => <option key={s.id} value={s.id}>{when(s.created_at_epoch)} · {s.top_count} בטבלה · {s.total_candidates_scored ?? "?"} נבדקו · {s.id.slice(0, 8)}</option>)}
        </select></label>
        {searches.length === 0 ? <p>טרם נשמרו חיפושים. ההיסטוריה מתחילה עם הפעלת התכונה.</p> : null}
        <div className="flex gap-3"><button disabled={busy || offset === 0} onClick={() => void load(Math.max(0, offset - 25))} className="underline disabled:opacity-40">חדשים יותר</button><button disabled={busy || !more} onClick={() => void load(offset + 25)} className="underline disabled:opacity-40">ישנים יותר</button></div>
      </section> : null}
      {audit ? <section className="space-y-4" aria-label="פירוט הדירוג">
        <h2 className="text-xl font-semibold">{when(audit.created_at_epoch)} · {audit.rows.length} מקומות מוצגים</h2>
        <p className="text-sm text-muted">עדיפות מוקדמת נבדקת לפני המאוחרת. ראיות איכות מפרידות רק בין מועמדים דומים עם מקור בר־השוואה. סדר התצוגה בתוך תיקו אינו יתרון בדירוג.</p>
        <div className="overflow-x-auto rounded-2xl border border-line"><table className="w-full min-w-[950px] text-sm">
          <caption className="sr-only">עשרת המקומות הראשונים לפי הסדר שנמסר למשפחה</caption>
          <thead className="bg-forest/10"><tr>{["מיקום", "מוסד", "חובה", "תקציב", "העדפות", "מה הכריע מול הבא?", "משקל / עדיפות"].map(h => <th key={h} scope="col" className={cell}>{h}</th>)}</tr></thead>
          <tbody>{audit.rows.map(row => {
            const deciding = row.comparison_vs_next?.deciding_dimension;
            const priority = row.criteria.find(c => c.parameter === deciding)?.priority;
            return <tr key={`${row.display_position}-${row.facility_id}`}>
              <td className={cell}>{row.rank_display || "לא נרשם"}{row.tie_status === "JOINT_RANK" ? <span className="block text-xs text-muted">תיקו</span> : null}</td>
              <th scope="row" className={cell}>{row.facility_name}<span className="block text-xs font-normal text-muted">{row.facility_id}</span></th>
              <td className={cell}>{row.must_status === "MUST_ELIGIBLE" ? "עבר" : row.must_status || "לא נרשם"}<span className="block text-xs text-muted">{row.must_pass.length} אושרו · {row.must_unknown.length} חסרים</span></td>
              <td className={cell}>{row.budget_exception === true ? "הרחבה מאושרת" : row.budget_exception === false ? "בתקציב" : "לא נרשם"}{row.budget_variance_pct !== null && row.budget_variance_pct !== undefined ? <span className="block text-xs">{row.budget_variance_pct > 0 ? "+" : ""}{row.budget_variance_pct}% מהתקציב</span> : null}</td>
              <td className={cell}>{row.nice_match.length} תואמות<span className="block text-xs text-muted">{row.nice_unknown.length} לא אומתו</span></td>
              <td className={cell}>{deciding ? name(deciding) : "אין השוואה מתועדת למקום הבא"}</td>
              <td className={cell}>{priority ? `עדיפות ${priority}` : deciding === "true_tie" ? "אין הבדל מוכח" : "לא תועד"}<span className="block text-xs text-muted">ללא משקל באחוזים</span></td>
            </tr>;
          })}</tbody></table></div>
        {audit.rows.length === 0 ? <p className="rounded-xl border border-line p-4">בחיפוש זה לא הוצגו המלצות. אין מקומות לדרג.</p> : null}
        <h3 className="text-lg font-semibold">פירוט הפרמטרים לכל מוסד</h3>
        {audit.rows.map(row => <details key={row.facility_id} className="rounded-xl border border-line p-4">
          <summary className="cursor-pointer font-medium">{row.rank_display} · {row.facility_name} — פתיחת פרמטרים וראיות</summary>
          <p className="my-3 text-sm">{row.comparison_vs_next?.why_ranked_above || "לא נרשמה השוואה למקום הבא."}</p>
          {row.snapshot_status !== "RECORDED" ? <p role="status">צילום ההשוואה חסר. אין להסיק ממנו סדר עדיפויות.</p> : null}
          <p className="my-2 text-sm">תנאי חובה שאושרו: {row.must_pass.join(", ") || "לא נרשמו"}</p>
          <p className="my-2 text-sm">מידע חסר בתנאי חובה: {row.must_unknown.join(", ") || "אין"} · העדפות שלא אומתו: {row.nice_unknown.join(", ") || "אין"}</p>
          <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-sm"><thead><tr>{["עדיפות", "פרמטר", "ערך שנבדק", "תפקיד בדירוג", "מקור"].map(h => <th key={h} scope="col" className={cell}>{h}</th>)}</tr></thead>
            <tbody>{row.criteria.map(c => <tr key={c.parameter}><td className={cell}>{c.priority ?? "—"}</td><th scope="row" className={cell}>{name(c.parameter)}</th><td className={cell}><bdi>{value(c.value)}</bdi></td><td className={cell}>{c.role === "ORDERED_CRITERION" ? "קריטריון לפי סדר; ערך מיון נמוך קודם" : c.role === "USED_TO_SEPARATE" ? "הפריד בין מועמדים בקבוצה" : c.evidence_state === "UNKNOWN" ? "חסר; לא שימש כהוכחה שלילית" : "קיים; לא שימש להפרדה"}{c.direction ? <span className="block text-xs text-muted">{c.direction === "higher" ? "ערך גבוה עדיף" : "ערך נמוך עדיף"}</span> : null}</td><td className={cell}>{c.source || "אין מקור מתועד"}</td></tr>)}</tbody></table></div>
        </details>)}
        <details className="rounded-xl border border-line p-4"><summary className="cursor-pointer">שלבי הסינון והיקף החיפוש</summary><pre dir="ltr" className="mt-3 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(audit.pipeline_trace, null, 2)}</pre></details>
      </section> : null}
    </div>
  </main>;
}
