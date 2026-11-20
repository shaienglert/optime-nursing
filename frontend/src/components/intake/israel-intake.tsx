"use client";

import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useQuestionnaire, type QuestionnaireState } from "@/context/questionnaire-context";
import { getApiBaseUrl, joinApiUrl } from "@/lib/api";
import { QUESTIONNAIRE_SESSION_KEY, saveSessionJson } from "@/lib/search-session";

import { IntakeIcon } from "./intake-icons";
import styles from "./israel-intake.module.css";

type Israel = NonNullable<QuestionnaireState["israelMarket"]>;
type Draft = { israel: Israel; notes: string };
type Option = { value: string; label: string; hint?: string; icon?: string };
type Info = { points: string[]; source: { label: string; href: string } };
type Step = {
  id: string;
  prompt: string;
  // Short label for the summary screen.
  short?: string;
  sub?: string;
  kind: "single" | "multi" | "text" | "city" | "info";
  info?: Info;
  options?: Option[];
  optionsFor?: (draft: Draft) => Option[];
  show?: (draft: Draft) => boolean;
  get: (draft: Draft) => string;
  set: (draft: Draft, value: string) => Draft;
  optional?: boolean;
};

const israelField = <K extends keyof Israel>(key: K, parse: (value: string) => Israel[K] = (v) => v as Israel[K]) => ({
  get: (d: Draft) => (d.israel[key] === null || d.israel[key] === undefined ? "" : String(d.israel[key])),
  set: (d: Draft, value: string): Draft => ({ ...d, israel: { ...d.israel, [key]: parse(value) } }),
});

const toNumber = (value: string) => (value ? Number(value) : null);

const STEPS: Step[] = [
  {
    id: "relationship",
    prompt: "עבור מי אתם מחפשים מסגרת?",
    kind: "single",
    short: "עבור",
    options: [
      { value: "אמא", label: "אמא", icon: "mother" },
      { value: "אבא", label: "אבא", icon: "father" },
      { value: "סבתא", label: "סבתא", icon: "grandparent" },
      { value: "סבא", label: "סבא", icon: "grandparent" },
      { value: "הורים", label: "שני ההורים", icon: "couple" },
      { value: "בן/בת זוג", label: "בן/בת זוג", icon: "couple" },
      { value: "עבורי", label: "עבורי", icon: "self" },
      { value: "קרוב/ה אחר/ת", label: "קרוב/ה אחר/ת", icon: "relative" },
    ],
    get: (d) => d.israel.relationship ?? "",
    set: (d, v) => ({ ...d, israel: { ...d.israel, relationship: v, isCouple: v === "הורים" ? true : d.israel.isCouple } }),
  },
  {
    id: "priority",
    prompt: "מה הכי חשוב היום?",
    short: "הכי חשוב",
    sub: "נתחיל מזה. זה עוזר לנו להציג קודם את המקומות הנכונים.",
    kind: "single",
    options: [
      { value: "MEDICAL", label: "השגחה רפואית", icon: "medical" },
      { value: "SOCIAL", label: "חברה ועשייה", icon: "social" },
      { value: "SAFETY", label: "מקום מוגן ובטוח", icon: "shield" },
      { value: "PEACE_OF_MIND", label: "שקט נפשי למשפחה", icon: "heart" },
    ],
    ...israelField("priority"),
  },
  {
    id: "ageGroup",
    prompt: "מה הגיל בערך?",
    kind: "single",
    options: ["מתחת ל-70", "70–79", "80–89", "90 ומעלה"].map((v) => ({ value: v, label: v })),
    ...israelField("ageGroup"),
  },
  {
    id: "functionalLevel",
    prompt: "מה המצב התפקודי היום?",
    kind: "single",
    options: [
      { value: "INDEPENDENT", label: "עצמאי/ת", hint: "מתלבש/ת, מתרחץ/ת ואוכל/ת בלי עזרה" },
      { value: "FRAIL", label: "תשוש/ה", hint: "צריך/ה עזרה חלקית, אבל מתנייד/ת בעצמו/ה" },
      { value: "NURSING", label: "סיעודי/ת", hint: "תלוי/ה בעזרה ברוב פעולות היום-יום" },
      { value: "COMPLEX_NURSING", label: "סיעודי/ת מורכב/ת", hint: "סיעודי עם מצב רפואי מורכב, למשל פצעי לחץ. בדרך כלל נקבע בבית החולים" },
      { value: "COGNITIVE_FRAIL", label: "תשוש/ת נפש", hint: "ירידה קוגניטיבית או דמנציה שמחייבת השגחה" },
      { value: "UNCLEAR", label: "לא בטוחים", hint: "לא נציג מסגרת כמתאימה עד שזה יתברר" },
    ],
    ...israelField("functionalLevel"),
  },
  {
    id: "complexInfo",
    prompt: "סיעוד מורכב: הסידור עובר דרך קופת החולים",
    kind: "info",
    show: (d) => d.israel.functionalLevel === "COMPLEX_NURSING",
    info: {
      points: [
        "הסידור במחלקה לסיעוד מורכב הוא באחריות קופת החולים, ויש בו השתתפות עצמית של המטופל.",
        "מי שמאושפז עכשיו בבית חולים פונה לעובד/ת הסוציאלי/ת במחלקה.",
        "אסור לקופה לעכב את הסידור רק כי ההשתתפות העצמית עוד לא הוסדרה.",
        "לכן לא נשאל על מימון. נציג רק מוסדות שיש בהם מחלקה לסיעוד מורכב.",
      ],
      source: { label: "כל זכות: סידור לחולים סיעודיים מורכבים", href: "https://www.kolzchut.org.il/he/סידור_מוסדי_עבור_חולים_סיעודיים_מורכבים" },
    },
    get: () => "",
    set: (d) => d,
    optional: true,
  },
  {
    id: "fundingPathway",
    prompt: "איך מתכננים לממן את המסגרת?",
    kind: "single",
    show: (d) => d.israel.functionalLevel !== "COMPLEX_NURSING",
    options: [
      { value: "MOH_CODE", label: "קוד של משרד הבריאות", hint: "השתתפות המדינה באשפוז סיעודי או תשו״ן" },
      { value: "WELFARE_ASSISTANCE", label: "סיוע של משרד הרווחה", hint: "דרך המחלקה לשירותים חברתיים" },
      { value: "PRIVATE", label: "באופן פרטי" },
      { value: "UNCLEAR", label: "עוד לא יודעים" },
    ],
    ...israelField("fundingPathway"),
  },
  {
    id: "codeInfo",
    prompt: "כדאי לדעת: קוד של משרד הבריאות",
    kind: "info",
    show: (d) => d.israel.functionalLevel !== "COMPLEX_NURSING" && d.israel.fundingPathway === "UNCLEAR",
    info: {
      points: [
        "המדינה מסייעת במימון מקום במוסד לסיעודיים או לתשושי נפש. הדרך עוברת בוועדה גריאטרית שקובעת את המסגרת המתאימה.",
        "גובה ההשתתפות נקבע במבחן הכנסות של ההורה, בן/בת הזוג והילדים הבגירים. ההשתתפות של כל ילד נקבעת לפי ההכנסות שלו.",
        "אפשר לממש את הקוד רק במוסד שיש לו הסכם עם משרד הבריאות.",
        "מי שמקבל גמלת סיעוד מביטוח לאומי לא יהיה זכאי לה במחלקה סיעודית או במחלקה לתשושי נפש.",
        "בינתיים לא נגביל את התוצאות לפי מימון. אפשר לחזור ולבחור מסלול בכל שלב.",
      ],
      source: { label: "כל זכות: אשפוז בקוד", href: "https://www.kolzchut.org.il/he/סיוע_במימון_סידור_מוסדי_לקשישים_סיעודיים_ותשושי_נפש_(אשפוז_בקוד)" },
    },
    get: () => "",
    set: (d) => d,
    optional: true,
  },
  {
    id: "monthlyBudgetIls",
    prompt: "מה התקציב החודשי?",
    kind: "single",
    show: (d) => d.israel.fundingPathway === "PRIVATE",
    options: [6000, 9000, 12000, 15000, 20000, 25000, 30000].map((n) => ({ value: String(n), label: `עד ₪${n.toLocaleString("he-IL")}` })),
    ...israelField("monthlyBudgetIls", toNumber),
  },
  {
    id: "isCouple",
    prompt: "המקום מיועד לאדם אחד או לזוג?",
    kind: "single",
    options: [
      { value: "false", label: "לאדם אחד" },
      { value: "true", label: "לבני זוג", hint: "נציג רק מוסדות שמקבלים זוגות" },
    ],
    get: (d) => (d.israel.isCouple === true ? "true" : d.israel.isCouple === false ? "false" : ""),
    set: (d, v) => ({ ...d, israel: { ...d.israel, isCouple: v === "true", partnerSameLevel: v === "true" ? d.israel.partnerSameLevel : null } }),
  },
  {
    id: "partnerSameLevel",
    prompt: "שני בני הזוג באותו מצב תפקודי?",
    kind: "single",
    show: (d) => d.israel.isCouple === true,
    options: [
      { value: "true", label: "כן" },
      { value: "false", label: "לא", hint: "למשל אחד עצמאי והשני סיעודי" },
    ],
    get: (d) => (d.israel.partnerSameLevel === true ? "true" : d.israel.partnerSameLevel === false ? "false" : ""),
    set: (d, v) => ({ ...d, israel: { ...d.israel, partnerSameLevel: v === "true" } }),
  },
  {
    id: "bedridden",
    prompt: "האם ההורה מרותק/ת למיטה?",
    kind: "single",
    show: (d) => ["NURSING", "COMPLEX_NURSING", "COGNITIVE_FRAIL", "UNCLEAR"].includes(d.israel.functionalLevel),
    options: [
      { value: "true", label: "כן", hint: "נציג רק מוסדות שמגינים על מרותקים בזמן אזעקה" },
      { value: "false", label: "לא" },
    ],
    get: (d) => (d.israel.bedridden === true ? "true" : d.israel.bedridden === false ? "false" : ""),
    set: (d, v) => ({ ...d, israel: { ...d.israel, bedridden: v === "true" } }),
  },
  {
    id: "medicalNeeds",
    prompt: "יש צורך רפואי מיוחד?",
    kind: "multi",
    optional: true,
    show: (d) => d.israel.functionalLevel !== "INDEPENDENT",
    options: [
      { value: "VENTILATION", label: "מונשם/ת" },
      { value: "WANDERING", label: "נוטה לשוטט / צריך מחלקה סגורה" },
      { value: "PEG", label: "הזנה דרך PEG" },
      { value: "NG_TUBE", label: "זונדה" },
    ],
    get: (d) => (d.israel.medicalNeeds ?? []).join(","),
    set: (d, v) => ({ ...d, israel: { ...d.israel, medicalNeeds: (v ? v.split(",") : []) as Israel["medicalNeeds"] } }),
  },
  {
    id: "setting",
    prompt: "איזו סביבה מתאימה?",
    short: "סביבה",
    kind: "single",
    options: [
      { value: "URBAN", label: "עירונית", hint: "קרוב לחנויות ולתחבורה", icon: "city" },
      { value: "RURAL", label: "כפרית", hint: "ירוק, שקט ומרווח", icon: "village" },
      { value: "", label: "לא משנה" },
    ],
    ...israelField("setting"),
    optional: true,
  },
  {
    id: "styles",
    prompt: "איזה סגנון של מקום?",
    short: "סגנון",
    sub: "אפשר לבחור יותר מאחד.",
    kind: "multi",
    optional: true,
    options: [
      { value: "LUXURY", label: "יוקרתי", icon: "luxury" },
      { value: "MODERN", label: "מודרני", icon: "modern" },
      { value: "BOUTIQUE", label: "בוטיק", icon: "boutique" },
      { value: "HOMEY", label: "ביתי", icon: "homey" },
    ],
    get: (d) => (d.israel.styles ?? []).join(","),
    set: (d, v) => ({ ...d, israel: { ...d.israel, styles: (v ? v.split(",") : []) as Israel["styles"] } }),
  },
  {
    id: "dayRhythm",
    prompt: "מה ישמח יותר ביום-יום?",
    short: "ביום-יום",
    kind: "single",
    options: [
      { value: "PRIVATE_SPACE", label: "מרחב אישי", hint: "חדר משלו או משלה", icon: "privateSpace" },
      { value: "PEOPLE_AROUND", label: "אנשים מסביב", hint: "אווירה חברתית ותוססת", icon: "social" },
      { value: "STRUCTURED", label: "סדר יום מוגדר", hint: "שגרה קבועה וידועה מראש", icon: "structured" },
      { value: "FLEXIBLE", label: "גמישות וחידושים", hint: "כל יום קצת אחר", icon: "flexible" },
    ],
    ...israelField("dayRhythm"),
    optional: true,
  },
  {
    id: "activities",
    prompt: "במה ישמח להשתתף?",
    short: "פעילויות",
    sub: "אפשר לבחור כמה.",
    kind: "multi",
    optional: true,
    options: [
      { value: "GARDENING", label: "גינון", icon: "gardening" },
      { value: "CRAFTS", label: "מלאכת יד", icon: "crafts" },
      { value: "GAMES", label: "משחקים", icon: "games" },
      { value: "MUSIC", label: "מוזיקה ושירה", icon: "music" },
      { value: "LECTURES", label: "הרצאות ותרבות", icon: "lectures" },
      { value: "MOVEMENT", label: "תנועה והתעמלות", icon: "movement" },
      { value: "OUTINGS", label: "טיולים ויציאות", icon: "outings" },
      { value: "SPIRITUAL", label: "שיעורים ותפילה", icon: "spiritual" },
    ],
    get: (d) => (d.israel.activities ?? []).join(","),
    set: (d, v) => ({ ...d, israel: { ...d.israel, activities: v ? v.split(",") : [] } }),
  },
  {
    id: "language",
    prompt: "באיזו שפה הכי נוח לדבר?",
    kind: "single",
    options: [
      ["HE", "עברית"], ["RU", "רוסית"], ["AR", "ערבית"], ["EN", "אנגלית"], ["AM", "אמהרית"],
      ["YI", "יידיש"], ["FR", "צרפתית"], ["ES", "ספרדית"], ["RO", "רומנית"],
    ].map(([value, label]) => ({ value, label })),
    ...israelField("language"),
  },
  {
    id: "community",
    prompt: "איזו אווירה מתאימה לכם?",
    kind: "single",
    options: [
      ["", "אין העדפה"], ["SECULAR", "חילונית"], ["TRADITIONAL", "מסורתית"], ["RELIGIOUS", "דתית"], ["HAREDI", "חרדית"],
      ["MUSLIM", "מוסלמית"], ["CHRISTIAN", "נוצרית"], ["DRUZE", "דרוזית"],
    ].map(([value, label]) => ({ value, label, hint: value ? "מוסדות מתאימים יופיעו קודם" : undefined })),
    ...israelField("community"),
    optional: true,
  },
  {
    id: "kashrut",
    prompt: "כשרות",
    kind: "single",
    show: (d) => !["MUSLIM", "CHRISTIAN", "DRUZE"].includes(d.israel.community ?? ""),
    options: [
      { value: "", label: "לא משנה" },
      { value: "KOSHER", label: "כשר" },
      { value: "MEHADRIN", label: "כשר למהדרין" },
    ],
    ...israelField("kashrut"),
    optional: true,
  },
  {
    id: "shabbat",
    prompt: "חשוב שבמוסד שומרים שבת?",
    kind: "single",
    show: (d) => ["TRADITIONAL", "RELIGIOUS", "HAREDI"].includes(d.israel.community ?? ""),
    options: [
      { value: "IMPORTANT", label: "כן, חשוב" },
      { value: "", label: "לא משנה" },
    ],
    ...israelField("shabbat"),
    optional: true,
  },
  {
    id: "sameGenderCare",
    prompt: "חשוב שהטיפול האישי (רחצה, הלבשה) ייעשה בידי מטפל/ת מאותו מגדר?",
    kind: "single",
    options: [
      { value: "IMPORTANT", label: "כן, חשוב", hint: "מוסדות שמאפשרים זאת יופיעו גבוה יותר" },
      { value: "", label: "לא משנה" },
    ],
    ...israelField("sameGenderCare"),
    optional: true,
  },
  {
    id: "shelterNeed",
    prompt: "מיגון: מה הכי רחוק שמקובל עליכם?",
    kind: "single",
    options: [
      { value: "ROOM", label: "ממ״ד בתוך החדר או הדירה", hint: "בלי לצאת מהחדר בזמן אזעקה" },
      { value: "FLOOR", label: "מרחב מוגן באותה קומה", hint: "בלי מדרגות ובלי לצאת מהבניין" },
      { value: "", label: "לא קריטי לנו" },
    ],
    ...israelField("shelterNeed"),
    optional: true,
  },
  {
    id: "shelterIsCondition",
    prompt: "להציג רק מוסדות שעומדים בזה?",
    kind: "single",
    show: (d) => Boolean(d.israel.shelterNeed),
    options: [
      { value: "true", label: "כן, זה תנאי", hint: "מוסד עם מיגון רחוק יותר לא יוצג" },
      { value: "false", label: "לא, רק להעדיף", hint: "מוסדות עם מיגון קרוב יופיעו קודם" },
    ],
    get: (d) => (d.israel.shelterIsCondition === true ? "true" : d.israel.shelterIsCondition === false ? "false" : ""),
    set: (d, v) => ({ ...d, israel: { ...d.israel, shelterIsCondition: v === "true" } }),
  },
  {
    id: "depositCapIls",
    prompt: "בדיור מוגן יש לרוב פיקדון. עד כמה אתם מוכנים להפקיד?",
    kind: "single",
    show: (d) => d.israel.fundingPathway === "PRIVATE" && ["INDEPENDENT", "FRAIL"].includes(d.israel.functionalLevel),
    options: [
      { value: "0", label: "בלי פיקדון", hint: "רק מסלול חודשי" },
      { value: "500000", label: "עד ₪500,000" },
      { value: "1000000", label: "עד ₪1,000,000" },
      { value: "1500000", label: "עד ₪1,500,000" },
      { value: "2500000", label: "עד ₪2,500,000" },
      { value: "", label: "עוד לא יודעים" },
    ],
    ...israelField("depositCapIls", (v) => (v === "" ? null : Number(v))),
    optional: true,
  },
  {
    id: "minBedrooms",
    prompt: "כמה חדרי שינה נפרדים נדרשים בדירה?",
    sub: "סופרים חדרי שינה בלבד, בלי הסלון.",
    kind: "single",
    optional: true,
    options: [1, 2, 3, 4].map((n) => ({ value: String(n), label: `לפחות ${n}` })),
    ...israelField("minBedrooms", toNumber),
  },
  {
    id: "privateCaregiver",
    prompt: "האם חייבים לאפשר מטפל/ת פרטי/ת מטעמכם?",
    kind: "single",
    optional: true,
    options: [
      { value: "VISITS", label: "כן, מגיע/ה לטפל בביקורים" },
      { value: "LIVE_IN", label: "כן, מתגורר/ת עם הדייר/ת" },
      { value: "UNCLEAR", label: "כן, סידור המגורים עוד לא ידוע" },
    ],
    ...israelField("privateCaregiver"),
  },
  {
    id: "parkingType",
    prompt: "איזו חניה נדרשת?",
    kind: "single",
    optional: true,
    options: [
      { value: "REGULAR", label: "כל חניה לדיירים" },
      { value: "ACCESSIBLE", label: "חניה נגישה" },
      { value: "COVERED", label: "חניה מקורה" },
    ],
    ...israelField("parkingType"),
  },
  {
    id: "petRequired",
    prompt: "חיית מחמד חייבת לעבור עם הדייר/ת?",
    kind: "single",
    optional: true,
    options: [{ value: "true", label: "כן, חובה לאפשר חיית מחמד" }, { value: "", label: "לא נדרש" }],
    get: (d) => d.israel.petRequired ? "true" : "",
    set: (d, value) => ({ ...d, israel: { ...d.israel, petRequired: value === "true" ? true : undefined } }),
  },
  {
    id: "requiredDiets",
    prompt: "אילו תפריטים מיוחדים חייבים להיות זמינים?",
    kind: "multi",
    optional: true,
    options: [
      { value: "DIABETIC", label: "לסוכרתיים" },
      { value: "TEXTURE_MODIFIED", label: "מרקם מותאם (טחון או רך)" },
      { value: "VEGETARIAN", label: "צמחוני" },
      { value: "VEGAN", label: "טבעוני" },
      { value: "GLUTEN_FREE", label: "ללא גלוטן" },
      { value: "LOW_SALT", label: "דל מלח" },
      { value: "HALAL", label: "חלאל" },
    ],
    get: (d) => (d.israel.requiredDiets ?? []).join(","),
    set: (d, value) => ({ ...d, israel: { ...d.israel, requiredDiets: value ? value.split(",") : [] } }),
  },
  { id: "city", prompt: "באיזה יישוב או אזור?", kind: "city", ...israelField("city") },
  {
    id: "maxDistanceKm",
    prompt: "עד כמה רחוק מהיישוב הזה אפשר?",
    kind: "single",
    options: [
      { value: "5", label: "עד 5 ק״מ" },
      { value: "10", label: "עד 10 ק״מ" },
      { value: "20", label: "עד 20 ק״מ" },
      { value: "40", label: "עד 40 ק״מ" },
      { value: "", label: "בכל הארץ" },
    ],
    ...israelField("maxDistanceKm", toNumber),
    optional: true,
  },
  {
    id: "notes",
    prompt: "ספרו לנו במילים שלכם מה חשוב לכם",
    kind: "text",
    optional: true,
    get: (d) => d.notes,
    set: (d, value) => ({ ...d, notes: value }),
  },
];

const EMPTY: Draft = {
  israel: {
    relationship: "",
    ageGroup: "",
    functionalLevel: "" as Israel["functionalLevel"],
    fundingPathway: "" as Israel["fundingPathway"],
    city: "",
    maxDistanceKm: null,
    monthlyBudgetIls: null,
    medicalNeeds: [],
    isCouple: null,
    partnerSameLevel: null,
    sameGenderCare: "",
    community: "",
    kashrut: "",
    shabbat: "",
    language: "",
    shelterInRoom: "",
    shelterNeed: "",
    shelterIsCondition: null,
    bedridden: null,
    depositCapIls: null,
  },
  notes: "",
};

const optionsOf = (step: Step, draft: Draft): Option[] => step.optionsFor?.(draft) ?? step.options ?? [];

const answered = (step: Step, draft: Draft) => step.optional || step.get(draft).trim() !== "";

export function IsraelIntake() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [stepId, setStepId] = useState(STEPS[0].id);
  const [summary, setSummary] = useState(false);
  const [error, setError] = useState(false);
  const [localities, setLocalities] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetch(joinApiUrl(getApiBaseUrl(), "/api/il/localities"))
      .then((response) => (response.ok ? response.json() : { names: [] }))
      .then((body: { names?: string[] }) => {
        if (!cancelled) setLocalities(body.names ?? []);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  const cityKnown = (value: string) => localities.length === 0 || localities.includes(value.trim());

  const steps = useMemo(() => STEPS.filter((s) => !s.show || s.show(draft)), [draft]);
  const index = Math.max(0, steps.findIndex((s) => s.id === stepId));
  const step = steps[index];
  const progress = summary ? 100 : Math.round((index / steps.length) * 100);

  function go(nextIndex: number, current: Draft = draft) {
    const visible = STEPS.filter((s) => !s.show || s.show(current));
    if (nextIndex >= visible.length) setSummary(true);
    else setStepId(visible[Math.max(0, nextIndex)].id);
    setError(false);
  }

  function choose(value: string) {
    const next = step.set(draft, value);
    setDraft(next);
    const visible = STEPS.filter((s) => !s.show || s.show(next));
    go(visible.findIndex((s) => s.id === step.id) + 1, next);
  }

  function submit() {
    // Answers to questions that are no longer shown must not act as filters.
    const visibleIds = new Set(steps.map((s) => s.id));
    const israel: Israel = {
      ...draft.israel,
      medicalNeeds: visibleIds.has("medicalNeeds") ? draft.israel.medicalNeeds : [],
      kashrut: visibleIds.has("kashrut") ? draft.israel.kashrut : "",
      shabbat: visibleIds.has("shabbat") ? draft.israel.shabbat : "",
      partnerSameLevel: visibleIds.has("partnerSameLevel") ? draft.israel.partnerSameLevel : null,
      monthlyBudgetIls: visibleIds.has("monthlyBudgetIls") ? draft.israel.monthlyBudgetIls : null,
      depositCapIls: visibleIds.has("depositCapIls") ? draft.israel.depositCapIls : null,
      shelterIsCondition: draft.israel.shelterNeed ? draft.israel.shelterIsCondition : null,
      bedridden: visibleIds.has("bedridden") ? draft.israel.bedridden : null,
      // Complex nursing is arranged through the health fund; funding is explained, never asked.
      fundingPathway: visibleIds.has("fundingPathway") ? draft.israel.fundingPathway : ("" as Israel["fundingPathway"]),
    };
    const submission: QuestionnaireState = {
      ...state,
      // Free text goes to the shared AI interpreter like any other market.
      notes: draft.notes.trim(),
      budget: israel.monthlyBudgetIls ?? 0,
      israelMarket: israel,
    };
    saveSessionJson(QUESTIONNAIRE_SESSION_KEY, submission);
    setState(submission);
    router.push("/he/results");
  }

  const label = (s: Step) => {
    const value = s.get(draft);
    const options = optionsOf(s, draft);
    if (s.kind === "multi") {
      return value ? value.split(",").map((v) => options.find((o) => o.value === v)?.label ?? v).join(", ") : "אין";
    }
    const found = options.find((o) => o.value === value);
    if (found) return found.label;
    return value || "לא צוין";
  };

  const tileClass = (option: Option, active: boolean) =>
    [styles.tile, option.icon ? "" : styles.tileText, active ? styles.selected : ""].filter(Boolean).join(" ");
  const wide = (options: Option[]) => options.some((o) => o.hint && !o.icon) || options.some((o) => o.hint && o.hint.length > 24);

  const tile = (option: Option, active: boolean, onClick: () => void) => (
    <button key={option.value || "any"} type="button" aria-pressed={active} onClick={onClick} className={tileClass(option, active)}>
      {option.icon ? (
        <span className={styles.icon}>
          <IntakeIcon name={option.icon} />
        </span>
      ) : null}
      <span className={styles.label}>{option.label}</span>
      {option.hint ? <span className={styles.hint}>{option.hint}</span> : null}
      {active ? (
        <span className={styles.tick}>
          <IntakeIcon name="check" size={14} />
        </span>
      ) : null}
    </button>
  );

  return (
    <main dir="rtl" lang="he" className={styles.page}>
      <header className={styles.bar}>
        <div className={styles.barInner}>
          <OptimeStaticLogo href="/he" height={26} className={styles.brand} />
          {!summary && index > 0 ? (
            <button type="button" className={styles.back} onClick={() => go(index - 1)}>
              הקודם
            </button>
          ) : null}
        </div>
        <div
          className={styles.track}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-label="התקדמות בשאלון"
        >
          <div className={styles.fill} style={{ width: `${Math.max(progress, 3)}%` }} />
        </div>
      </header>

      <div className={styles.stage}>
        {!summary && step ? (
          <section key={step.id} className={styles.question} aria-labelledby={`q-${step.id}`}>
            <h1 id={`q-${step.id}`} className={styles.prompt}>{step.prompt}</h1>
            {step.sub ? <p className={styles.sub}>{step.sub}</p> : null}

            {step.kind === "info" && step.info ? (
              <div className={styles.info}>
                <ul className={styles.infoList}>
                  {step.info.points.map((point) => <li key={point}>{point}</li>)}
                </ul>
                <a className={styles.source} href={step.info.source.href} target="_blank" rel="noreferrer">
                  מקור: {step.info.source.label}
                </a>
              </div>
            ) : step.kind === "single" ? (
              <div className={`${styles.grid} ${wide(optionsOf(step, draft)) ? styles.gridWide : ""}`}>
                {optionsOf(step, draft).map((option) => tile(option, step.get(draft) === option.value && (option.value !== "" || answered(step, draft)), () => choose(option.value)))}
              </div>
            ) : step.kind === "multi" ? (
              <div className={`${styles.grid} ${wide(optionsOf(step, draft)) ? styles.gridWide : ""}`}>
                {optionsOf(step, draft).map((option) => {
                  const chosen = step.get(draft).split(",").filter(Boolean);
                  const active = chosen.includes(option.value);
                  const next = active ? chosen.filter((v) => v !== option.value) : [...chosen, option.value];
                  return tile(option, active, () => setDraft(step.set(draft, next.join(","))));
                })}
              </div>
            ) : step.kind === "city" ? (
              <>
                <input aria-label={step.prompt} list="il-localities" className={styles.input} value={step.get(draft)} onChange={(e) => setDraft(step.set(draft, e.target.value))} placeholder="למשל: חיפה" />
                <datalist id="il-localities">
                  {localities.map((name) => <option key={name} value={name} />)}
                </datalist>
                {step.get(draft).trim() && !cityKnown(step.get(draft)) ? (
                  <p className={styles.note}>לא מצאנו יישוב בשם הזה, ולכן לא נוכל לחשב מרחק. כדאי לבחור מהרשימה.</p>
                ) : null}
              </>
            ) : (
              <textarea aria-label={step.prompt} className={styles.textarea} value={step.get(draft)} onChange={(e) => setDraft(step.set(draft, e.target.value))} placeholder="למשל: חשוב לנו אוכל כשר ושיהיה צוות שמדבר רוסית" />
            )}

            {error ? <p role="alert" className={styles.alert}>צריך לענות על השאלה כדי להמשיך.</p> : null}
            {step.kind !== "single" || (step.optional && step.get(draft) !== "") ? (
              <div className={styles.actions}>
                <button type="button" className={styles.primary} onClick={() => (answered(step, draft) ? go(index + 1) : setError(true))}>
                  {step.kind === "info" ? "הבנתי, נמשיך" : step.kind === "multi" && !step.get(draft) ? "דילוג" : "המשך"}
                </button>
              </div>
            ) : null}
          </section>
        ) : (
          <section className={styles.question} aria-labelledby="summary-title">
            <h1 id="summary-title" className={styles.prompt}>זה מה שהבנו</h1>
            <p className={styles.sub}>אם משהו לא מדויק, אפשר לחזור ולתקן.</p>
            <div className={styles.summary}>
              {steps.filter((s) => s.get(draft) !== "").map((s) => (
                <div key={s.id} className={styles.row}>
                  <span className={styles.rowLabel}>{s.short ?? s.prompt}</span>
                  <span className={styles.rowValue}>{label(s)}</span>
                </div>
              ))}
            </div>
            {draft.israel.functionalLevel === "UNCLEAR" ? (
              <p className={styles.note}>המצב התפקודי עוד לא ברור. עד שיתברר, אף מסגרת לא תוצג כמתאימה.</p>
            ) : null}
            <div className={styles.actions}>
              <button type="button" className={styles.primary} onClick={submit}>נכון, להמשיך</button>
              <button type="button" className={styles.secondaryButton} onClick={() => { setSummary(false); setStepId(steps[0].id); }}>לתקן</button>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
