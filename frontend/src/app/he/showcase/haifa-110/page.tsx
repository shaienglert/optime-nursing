"use client";

import { useState } from "react";
import Link from "next/link";

const facility = {
  id: "IL-SYN-110",
  name: "מעונות הזהב חיפה 110",
  address: "רחוב לדוגמה 110, חיפה",
  capacity: 161,
  levels: ["תשושים", "סיעודיים", "תשושי נפש"],
  photos: [
    { src: "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1400&q=85", label: "אווירת מבנה ומרחבים" },
    { src: "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=1000&q=85", label: "המחשת חדר מגורים" },
    { src: "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=1000&q=85", label: "המחשת חלל משותף" },
    { src: "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1000&q=85", label: "המחשת אזור ישיבה" },
  ],
};
const eventExamples = [
  ["ראשון", "10:00", "התעמלות ותנועה"],
  ["שני", "11:30", "מוזיקה ושירה"],
  ["שלישי", "15:00", "מלאכת יד ויצירה"],
  ["רביעי", "10:30", "משחקים בהפעלה"],
  ["חמישי", "16:00", "מפגש חברתי"],
];
const care = [
  ["צוות רפואי", "אחות במקום 24 שעות, רופא מספר פעמים בשבוע, גריאטר בצוות"],
  ["טיפולים", "חמצן, קטטר, אינסולין, עירוי, טיפול בפצעי לחץ, טרכאוסטומיה וטיפול תומך"],
  ["הזנה", "PEG וזונדה — לפי דיווח המוסד הסינתטי"],
  ["מקצועות טיפול", "ריפוי בעיסוק"],
  ["שפות", "עברית, רוסית, ספרדית"],
  ["תזונה", "כשר; אפשרויות לסוכרתיים, דל מלח, צמחוני ומרקם מותאם"],
];
export default function IsraelSyntheticShowcase() {
  const [hero, setHero] = useState(0);
  const [notice, setNotice] = useState("");
  const [month, setMonth] = useState(0);
  const months = ["נובמבר 2026", "דצמבר 2026"];
  return <main dir="rtl" lang="he" className="min-h-screen bg-[#FDFBF7] text-[#294638]">
    <div className="bg-[#e8eee5] px-4 py-2 text-center text-xs font-semibold">הדגמה בלבד · מוסד סינתטי · התמונות להמחשה ואינן מתעדות את המקום · אין לבצע הזמנה אמיתית</div>
    <div className="mx-auto max-w-7xl px-5 pb-16">
      <header className="flex flex-wrap items-center justify-between gap-4 py-7">
        <Link href="/he" className="text-3xl font-bold tracking-tight">OO<span className="font-light">mnik</span></Link>
        <Link href="/he/facility/IL-SYN-110" className="text-sm underline underline-offset-4">צפייה ברשומת המקור באתר</Link>
        <button onClick={()=>document.getElementById("visit")?.scrollIntoView({behavior:"smooth"})} className="rounded-full bg-[#345c49] px-6 py-3 font-semibold text-white">לתיאום ביקור</button>
      </header>
      <p className="text-sm text-[#7b8c7c]">בית אבות סיעודי / חיפה / דף מוסד לדוגמה</p>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-5">
        <div><h1 className="text-4xl font-semibold md:text-5xl">{facility.name}</h1><p className="mt-3 text-[#65796a]">{facility.address} · 161 מיטות · גיל קבלה 70+</p></div>
        <div className="rounded-2xl border border-[#dbe3d8] bg-white p-5"><p className="text-xs text-[#718675]">מחיר התחלתי מדווח</p><p className="mt-1 text-3xl font-semibold">₪10,500 <span className="text-sm font-normal">לחודש</span></p><p className="text-xs text-[#718675]">חדר זוגי, תשושים · רשימת המתנה</p></div>
      </div>
      <div className="mt-8 grid gap-3 md:grid-cols-[1.7fr_1fr]">
        <div className="relative overflow-hidden rounded-3xl bg-[#e7e9e1]"><img src={facility.photos[hero].src} alt={facility.photos[hero].label} className="h-[380px] w-full object-cover"/><span className="absolute bottom-4 right-4 rounded-full bg-white/95 px-4 py-2 text-xs">{facility.photos[hero].label} · תמונת השראה בלבד</span></div>
        <div className="grid grid-cols-3 gap-3 md:grid-cols-1">{facility.photos.slice(1).map((p,i)=><button key={p.src} onClick={()=>setHero(i+1)} className="overflow-hidden rounded-2xl bg-[#e7e9e1]"><img src={p.src} alt={p.label} className="h-28 w-full object-cover md:h-[118px]"/></button>)}</div>
      </div>
      <nav className="mt-8 flex flex-wrap gap-2 border-b border-[#e3e9df] pb-5">{[["מחלקות","#departments"],["חדרים ומחירים","#rooms"],["טיפול ושירותים","#care"],["חיי קהילה","#life"],["אירועים","#events"],["שקיפות","#evidence"]].map(([label,href])=><a key={href} href={href} className="rounded-full bg-white px-5 py-2 text-sm shadow-sm hover:bg-[#e6eee7]">{label}</a>)}</nav>
      <section className="grid gap-10 py-12 lg:grid-cols-[1.6fr_1fr]">
        <div><p className="text-xs font-bold tracking-widest text-[#81957d]">להכיר את המקום</p><h2 className="mt-3 text-3xl font-semibold">סביבה ביתית, טיפול מקצועי ומענה לצרכים משתנים</h2><p className="mt-5 leading-8 text-[#617266]">המוסד הסינתטי מתואר כסביבה עירונית, ביתית, שקטה ורגועה. לפי נתוני הפיילוט הוא מקבל תשושים, סיעודיים ותשושי נפש ומספק שירותי טיפול רפואי, פעילויות חברתיות ותזונה מותאמת. הדף מציג כיצד תיראה חוויית המידע למשפחות, ולא מתאר מוסד קיים.</p></div>
        <aside className="rounded-3xl bg-[#edf2ea] p-7"><h3 className="text-xl font-semibold">עיקרי המידע</h3><dl className="mt-5 space-y-4 text-sm">{[["מיטות", "161"],["קבלת זוגות","לא"],["קוד משרד הבריאות","כן — נתון סינתטי"],["שפות","עברית, רוסית, ספרדית"],["כשרות","כשר"],["רישיון","SYN-0110 · עד 15.11.2027 (סינתטי)"]].map(([k,v])=><div key={k} className="flex justify-between gap-3 border-b border-[#d7e0d4] pb-3"><dt className="text-[#657569]">{k}</dt><dd className="text-left font-semibold">{v}</dd></div>)}</dl></aside>
      </section>
      <section id="departments" className="py-10"><h2 className="text-3xl font-semibold">אוכלוסיות ורמות טיפול</h2><p className="mt-2 text-[#728172]">שלוש רמות הטיפול מופיעות ברשומה. מספר מחלקות ומיטות בכל מחלקה לא סופק.</p><div className="mt-6 grid gap-4 md:grid-cols-3">{facility.levels.map((x,i)=><article key={x} className="rounded-3xl border border-[#e1e7dc] bg-white p-7"><div className="mb-5 text-3xl text-[#88a18b]">0{i+1}</div><h3 className="text-2xl font-semibold">{x}</h3><p className="mt-3 text-sm leading-7 text-[#657669]">{["סיוע בפעולות היומיום לפי הערכת צרכים","טיפול סיעודי והשגחה לפי התאמה רפואית","מסגרת לתשושי נפש; השגחה למשוטטים אינה מאושרת ברשומה"][i]}</p><span className="mt-5 inline-block rounded-full bg-[#eef1e9] px-4 py-2 text-xs">זמינות: {["רשימת המתנה","צפי מקום בתוך חודש","רשימת המתנה"][i]}</span></article>)}</div></section>
      <section id="rooms" className="py-10"><h2 className="text-3xl font-semibold">חדרים ומחירים</h2><div className="mt-6 grid gap-5 md:grid-cols-2">{[["חדר זוגי לשני דיירים","החל מ־₪10,500 לחודש","רשימת המתנה"],["חדר ליחיד","מחיר בבירור","זמינות בבירור"]].map(([n,p,a])=><div key={n} className="overflow-hidden rounded-3xl bg-white shadow-sm"><img src="https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=1000&q=85" alt="תמונת חדר להמחשה בלבד" className="h-52 w-full object-cover"/><div className="p-6"><h3 className="text-xl font-semibold">{n}</h3><p className="mt-3 text-2xl font-semibold">{p}</p><p className="mt-2 text-sm text-[#758274]">{a} · שירותים ומקלחת צמודים בחלק מהחדרים</p></div></div>)}</div><p className="mt-4 text-sm text-[#738172]">לפי הרשומה: מזגן ומרפסת בחדר; המחיר כולל פעילויות וניקיון. מחיר סופי תלוי בהצעת המוסד.</p></section>
      <section id="care" className="py-10"><h2 className="text-3xl font-semibold">טיפול, נגישות ואורח חיים</h2><div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">{care.map(([a,b])=><article key={a} className="rounded-2xl border border-[#e3e8df] bg-white p-6"><h3 className="font-semibold">{a}</h3><p className="mt-3 text-sm leading-7 text-[#68786a]">{b}</p></article>)}</div><div className="mt-6 rounded-2xl bg-[#f0ede4] p-5 text-sm leading-7">מיגון: מקלט בבניין בקומה אחרת; זמן הגעה מדווח לדייר איטי — 2 דקות; דייר מרותק למיטה מועבר במיטה למרחב מוגן. יש מעלית, לחצן מצוקה ונגישות לכיסאות גלגלים. כל אלה נתוני פיילוט סינתטיים.</div></section>
      <section id="life" className="py-10"><h2 className="text-3xl font-semibold">חיי הקהילה</h2><p className="mt-4 max-w-3xl leading-8 text-[#647666]">ברשומה מצוינות פעילויות קבועות: יצירה, משחקים, התעמלות, מוזיקה, שירה, טיולים ויציאות. יש גינה והסעות. ביקורים מתקיימים בשעות קבועות; משפחות מקבלות עדכונים בפגישות צוות ובוואטסאפ.</p></section>
      <section id="events" className="py-10"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-3xl font-semibold">יומן פעילויות ואירועים</h2><p className="mt-2 text-sm text-[#768476]">אירועים לדוגמה בלבד, על בסיס סוגי הפעילות ברשומה. לא חובר יומן אמיתי.</p></div><div className="flex items-center gap-3"><button onClick={()=>setMonth(0)} className="rounded-full border px-4 py-2">הקודם</button><span className="font-semibold">{months[month]}</span><button onClick={()=>setMonth(1)} className="rounded-full border px-4 py-2">הבא</button></div></div><div className="mt-6 grid gap-3 md:grid-cols-5">{eventExamples.map(([day,time,event])=><div key={day} className="rounded-2xl bg-white p-5"><p className="text-xs font-semibold text-[#8c9c87]">{day}</p><h3 className="mt-4 font-semibold">{event}</h3><p className="mt-3 text-sm text-[#718071]">{time} · דוגמה</p></div>)}</div><p className="mt-5 rounded-xl border border-dashed border-[#a7b8a6] p-5 text-sm">חיבור עתידי: יומן המוסד, עדכונים בזמן אמת, הזמנת בני משפחה לאירועים ואישור השתתפות. אין חיבור פעיל בשלב זה.</p></section>
      <section id="evidence" className="py-10"><h2 className="text-3xl font-semibold">שקיפות ומקורות מידע</h2><div className="mt-5 grid gap-4 md:grid-cols-3">{[["נתוני מוסד","רשומה סינתטית IL-SYN-110 מתוך אתר OOmnik ישראל"],["מחיר","לפי המוסד הסינתטי; עודכן ב־11.11.2026"],["תמונות ויומן","תמונות השראה ואירועים לדוגמה; לא נמסרו על ידי מוסד אמיתי"]].map(([a,b])=><div key={a} className="rounded-2xl bg-[#edf1e9] p-6"><h3 className="font-semibold">{a}</h3><p className="mt-3 text-sm leading-6 text-[#67786b]">{b}</p></div>)}</div></section>
      <section id="visit" className="my-10 rounded-3xl bg-[#345c49] p-8 text-white md:p-12"><h2 className="text-3xl font-semibold">רוצים להכיר מקרוב?</h2><p className="mt-4 text-[#e2ece2]">זהו דף הדגמה למוסד סינתטי. בקשת ביקור אינה נשלחת למוסד.</p><div className="mt-6 flex flex-wrap gap-3"><button className="rounded-full bg-white px-6 py-3 font-semibold text-[#345c49]" onClick={()=>setNotice("תיאום ביקור לדוגמה: יש לחבר יומן זמין של מוסד אמיתי.")}>בקשת סיור</button><button className="rounded-full border border-white px-6 py-3" onClick={()=>setNotice("שאלות למשפחה יועברו דרך OOmnik לאחר חיבור מוסד אמיתי.")}>שאלה למוסד</button></div>{notice&&<p role="status" className="mt-5 text-sm">{notice}</p>}</section>
    </div>
  </main>;
}
