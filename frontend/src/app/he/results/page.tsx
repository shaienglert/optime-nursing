"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";
import { fetchIsraelResults, type IsraelResultCard, type IsraelResults } from "@/lib/israel-facility";
import { QUESTIONNAIRE_SESSION_KEY, loadSessionJson } from "@/lib/search-session";

import styles from "./results.module.css";

const MISSING_HE: Record<string, string> = {
  functionalLevel: "רמת התפקוד",
  fundingPathway: "מסלול המימון",
  city: "היישוב שממנו מחפשים",
};

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("he-IL");
}

function Card({ card }: { card: IsraelResultCard }) {
  const updated = formatDate(card.source.updated_at);
  const offer = card.prices.offers[0];
  return (
    <article className={styles.card} aria-labelledby={`r-${card.canonical_id}`}>
      <div className={styles.cardHead}>
        <span className={styles.rank} aria-label={`מקום ${card.rank}`}>
          {card.rank}
        </span>
        <div>
          <h2 id={`r-${card.canonical_id}`} className={styles.name}>
            {card.name}
          </h2>
          <p className={styles.meta}>
            {[card.facility_type, card.city, card.distance_km != null ? `${card.distance_km} ק"מ ממך` : null].filter(Boolean).join(", ")}
          </p>
        </div>
      </div>

      <div className={styles.columns}>
        <div>
          <h3 className={styles.groupTitle}>עומד בכל תנאי החובה</h3>
          <ul className={styles.ok}>
            {card.musts_met.map((m) => (
              <li key={m.key}>{m.label}</li>
            ))}
          </ul>
        </div>
        {card.preferences_met.length || card.preferences_not_met.length ? (
          <div>
            <h3 className={styles.groupTitle}>מול ההעדפות שלכם</h3>
            <ul className={styles.prefs}>
              {card.preferences_met.map((m) => (
                <li key={m.key} className={styles.prefYes}>
                  {m.label}
                </li>
              ))}
              {card.preferences_not_met.map((m) => (
                <li key={m.key} className={styles.prefNo}>
                  {m.label}: לא מתאים
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      {card.unknown.length ? (
        <p className={styles.unknown}>
          עוד לא ידוע: {card.unknown.map((u) => u.label).join(", ")}. כדאי לשאול את המוסד.
        </p>
      ) : null}

      <div className={styles.foot}>
        <div className={styles.price}>
          {offer ? <strong>{offer.text}</strong> : <strong>{card.prices.label ?? "מחיר בבירור"}</strong>}
          {card.budget?.label ? <span>{card.budget.label}</span> : null}
        </div>
        <Link href={`/he/facility/${encodeURIComponent(card.canonical_id)}`} className={styles.open}>
          לדף המוסד
        </Link>
      </div>
      <p className={styles.source}>
        {card.source.label}
        {updated ? `, עודכן ב־${updated}` : ""}
      </p>
    </article>
  );
}

export default function HebrewResults() {
  const [data, setData] = useState<IsraelResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [noAnswers, setNoAnswers] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const state = loadSessionJson<Record<string, unknown>>(QUESTIONNAIRE_SESSION_KEY);
      if (!state || !state.israelMarket) {
        await Promise.resolve();
        if (!cancelled) setNoAnswers(true);
        return;
      }
      try {
        const result = await fetchIsraelResults(state, String(state.notes ?? ""));
        if (!cancelled) setData(result);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "לא ניתן לטעון את התוצאות כרגע.");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main dir="rtl" lang="he" className={styles.page}>
      <header className={styles.bar}>
        <div className={styles.barInner}>
          <OptimeStaticLogo href="/he" height={26} className={styles.logo} />
          <Link href="/he/intake" className={styles.barLink}>
            שינוי התשובות
          </Link>
        </div>
      </header>

      <div className={styles.wrap}>
        {noAnswers ? (
          <section className={styles.notice}>
            <h1 className={styles.title}>עוד לא מילאתם את השאלון</h1>
            <Link href="/he/intake" className={styles.primary}>
              מתחילים
            </Link>
          </section>
        ) : error ? (
          <section className={styles.notice} role="alert">
            <h1 className={styles.title}>לא הצלחנו לטעון את התוצאות</h1>
            <p>{error}</p>
          </section>
        ) : !data ? (
          <p className={styles.loading} role="status">
            בודקים את כל המוסדות מול התשובות שלכם…
          </p>
        ) : data.status === "NEEDS_INPUT" ? (
          <section className={styles.notice}>
            <h1 className={styles.title}>חסר לנו עוד פרט אחד לפני שבודקים</h1>
            <p>כדי להציג רק מקומות שבאמת יכולים לקבל את ההורה, אנחנו צריכים לדעת: {(data.missing ?? []).map((m) => MISSING_HE[m] ?? m).join(", ")}.</p>
            <Link href="/he/intake" className={styles.primary}>
              חזרה לשאלון
            </Link>
          </section>
        ) : (
          <>
            <section className={styles.summary} aria-labelledby="summary-title">
              <h1 id="summary-title" className={styles.title}>
                {data.funnel && data.funnel.passed > 0
                  ? `${data.funnel.passed} מקומות עומדים בכל תנאי החובה שלכם`
                  : "אין כרגע מקום שעומד בכל תנאי החובה שלכם"}
              </h1>
              {data.funnel ? (
                <p className={styles.lede}>
                  בדקנו {data.funnel.universe} מוסדות.
                  {data.funnel.shown < data.funnel.passed ? ` מוצגים ${data.funnel.shown} המתאימים ביותר.` : ""} הסדר: קודם מקומות שעונים על יותר
                  מההעדפות שלכם, אחר כך מקומות עם פחות העדפות שלא מתקיימות, ובסוף לפי המרחק.
                </p>
              ) : null}
              {data.musts?.length ? (
                <p className={styles.chips}>
                  <span>תנאי החובה שלכם:</span>
                  {data.musts.map((m) => (
                    <span key={m.key} className={styles.chip}>
                      {m.label}
                    </span>
                  ))}
                </p>
              ) : null}
              {data.interpretation.status === "UNPROCESSED" && data.interpretation.message ? (
                <p className={styles.warn}>{data.interpretation.message}</p>
              ) : null}
              {data.interpretation.clarification_question ? (
                <p className={styles.warn}>שאלה שתעזור לדייק: {data.interpretation.clarification_question}</p>
              ) : null}
            </section>

            {data.oomniker && (data.oomniker.lines.length || data.oomniker.actions.length) ? (
              <section className={styles.oomniker} aria-labelledby="oomniker-title">
                <h2 id="oomniker-title">מה כדאי לדעת</h2>
                {data.oomniker.lines.map((line) => (
                  <p key={line}>{line}</p>
                ))}
                {data.oomniker.actions.map((line) => (
                  <p key={line} className={styles.action}>
                    {line}
                  </p>
                ))}
              </section>
            ) : null}

            <div className={styles.list}>
              {data.results.map((card) => (
                <Card key={card.canonical_id} card={card} />
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
