import type { Metadata } from "next";
import Link from "next/link";

import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";

import styles from "./landing.module.css";

export const metadata: Metadata = {
  title: "OOMNIK | מוצאים מקום שמתאים באמת",
  description:
    "OOMNIK מראה למשפחות רק דיור מוגן, בתי אבות ומחלקות סיעודיות שיכולים לקבל את ההורה שלהן, לפי רמת התפקוד, המימון והצרכים הרפואיים. חינם למשפחות.",
};

const GETS = [
  {
    title: "רק מקומות שיכולים לקבל אותו",
    body: "רמת תפקוד, מסלול מימון, טיפול רפואי ומיגון למי שמרותק למיטה הם תנאי חובה. מקום שלא עומד בהם לא מופיע ברשימה, גם אם הוא יפה.",
  },
  {
    title: "הסבר לכל התאמה",
    body: "ליד כל מקום כתוב למה הוא כאן, מה עוד לא ידוע ומה כדאי לשאול בביקור.",
  },
  {
    title: "מחירים בלי הפתעות",
    body: "מחיר התחלתי שהמוסד עצמו פרסם, עם התאריך שבו אומת. מוסד שלא מפרסם מחיר מסומן \"מחיר בבירור\".",
  },
  {
    title: "פנייה ישירה למוסד",
    body: "שולחים שאלה מתוך OOMNIK ומקבלים את התשובה בקישור אישי. לא צריך להשאיר טלפון כדי לראות תוצאות.",
  },
];

const STEPS = [
  { title: "עונים על כמה שאלות", body: "על ההורה, על המימון ועל מה שחשוב לכם. כל תשובה אפשר לשנות אחר כך." },
  { title: "מקבלים רשימה מסודרת", body: "קודם המקומות שעונים על כל התנאים, ובתוכם קודם מה שמתאים לכם יותר." },
  { title: "פונים, מבקרים, מחליטים", body: "שואלים את המוסדות ישירות, משווים, ובוחרים בקצב שלכם." },
];

const PRINCIPLES = [
  "מוסד לא יכול לשלם כדי להופיע גבוה יותר. הסדר נקבע רק לפי ההתאמה.",
  "כשמשהו לא ידוע, כתוב שהוא לא ידוע. אנחנו לא מנחשים בשבילכם.",
  "המידע מגיע מהמוסדות עצמם, וליד כל פרט כתוב מתי עודכן.",
];

export default function HebrewLanding() {
  return (
    <main dir="rtl" lang="he" className={styles.page}>
      <header className={styles.bar}>
        <div className={styles.barInner}>
          <OptimeStaticLogo href="/he" height={26} className={styles.logo} />
          <Link href="/he/intake" className={styles.barCta}>
            מתחילים
          </Link>
        </div>
      </header>

      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroText}>
          <h1 id="hero-title" className={styles.title}>
            מוצאים להורה מקום שבאמת יכול לקבל אותו.
          </h1>
          <p className={styles.lede}>
            OOMNIK עובר על דיור מוגן, בתי אבות ומחלקות סיעודיות, ומראה לכם רק את המקומות שמתאימים לרמת התפקוד, למימון
            ולצרכים הרפואיים של ההורה שלכם. חינם למשפחות.
          </p>
          <div className={styles.actions}>
            <Link href="/he/intake" className={styles.primary}>
              מתחילים את החיפוש
            </Link>
            <a href="#how" className={styles.secondary}>
              איך זה עובד
            </a>
          </div>
        </div>

        <figure className={styles.example} aria-label="דוגמה לכרטיס התאמה">
          <figcaption className={styles.exampleCaption}>כך נראית התאמה (דוגמה להמחשה)</figcaption>
          <div className={styles.card}>
            <p className={styles.cardName}>בית אבות לדוגמה, חיפה</p>
            <p className={styles.cardMeta}>12 ק&quot;מ ממך</p>
            <ul className={styles.checks}>
              <li>מקבל סיעודיים</li>
              <li>הסכם קוד עם משרד הבריאות</li>
              <li>מרותקים למיטה מוגנים בחדר בזמן אזעקה</li>
            </ul>
            <p className={styles.unknown}>עוד לא ידוע: האם יש מקום פנוי החודש. כדאי לשאול.</p>
            <p className={styles.price}>
              החל מ־₪14,500 לחודש
              <span>לפי המוסד, אומת ב־1.11</span>
            </p>
          </div>
        </figure>
      </section>

      <section className={styles.section} aria-labelledby="gets-title">
        <h2 id="gets-title" className={styles.sectionTitle}>
          מה מקבלים מאיתנו
        </h2>
        <div className={styles.gets}>
          {GETS.map((item) => (
            <div key={item.title} className={styles.get}>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="how" className={styles.section} aria-labelledby="how-title">
        <h2 id="how-title" className={styles.sectionTitle}>
          איך זה עובד
        </h2>
        <ol className={styles.steps}>
          {STEPS.map((step) => (
            <li key={step.title}>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className={styles.section} aria-labelledby="who-title">
        <h2 id="who-title" className={styles.sectionTitle}>
          מי אנחנו
        </h2>
        <p className={styles.prose}>
          OOMNIK נבנה כי חיפוש מסגרת להורה הוא אחת ההחלטות הקשות שמשפחה מקבלת, ורוב המידע שזמין היום הוא פרסומי. אנחנו
          עובדים לפי שלושה כללים:
        </p>
        <ul className={styles.principles}>
          {PRINCIPLES.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className={styles.facilities} aria-labelledby="facilities-title">
        <h2 id="facilities-title" className={styles.sectionTitle}>
          מנהלים מוסד?
        </h2>
        <p className={styles.prose}>
          ההרשמה ל־OOMNIK בחינם. כל מוסד מקבל קישור אישי, ממלא בו את הפרטים שלו ומקבל דף משלו עם שירותים, מחירים, תמונות
          ופעילויות. משפחות רואות את המוסד רק כשהוא באמת מתאים להן, כך שהפניות שמגיעות הן רלוונטיות.
        </p>
      </section>

      <section className={styles.closing}>
        <h2 className={styles.closingTitle}>מתחילים מהשאלה הראשונה.</h2>
        <Link href="/he/intake" className={styles.primary}>
          מתחילים את החיפוש
        </Link>
      </section>

      <footer className={styles.footer}>
        <p>OOMNIK נמצא כרגע בפיילוט.</p>
      </footer>
    </main>
  );
}
