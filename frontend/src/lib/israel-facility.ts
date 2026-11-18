export type IsraelFacilityPage = {
  canonical_id: string;
  name: string;
  registration_status: "REGISTERED" | "NOT_REGISTERED";
  from_list: {
    facility_type: string | null;
    city: string | null;
    district: string | null;
    operator_name: string | null;
    ownership_type: string | null;
    phone: string | null;
    website: string | null;
    license_id: string | null;
    moh_code_agreement: "YES" | "NO" | null;
    departments: string[];
    religion_attitude: string[];
    source_name: string;
  };
  from_facility: {
    functional_levels_served: string[];
    moh_code_agreement: "YES" | "NO";
    license_authority: string;
    license_id: string;
    license_expiration_date: string;
    monthly_price_ils: number | null;
    deposit_ils: number | null;
  } | null;
  prices: {
    status: "PUBLISHED" | "ON_REQUEST" | "NOT_REGISTERED";
    label: string | null;
    verified_at?: string | null;
    source?: string;
    offers: { text: string; availability: string; track: string; level: string; room_type: string }[];
  };
  facility_details: { key: string; title: string; items: { key: string; label: string; value: string }[] }[];
  family_feedback: FeedbackSummary;
  photos: { url: string; caption: string | null; category: string }[];
  activities: { category: string; availability: string; confidence: number }[];
  data_quality_flags: string[];
};

export type IsraelFacilityListItem = { canonical_id: string; name: string; facility_type: string; city: string | null };

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api/backend${path}`);
  if (!response.ok) throw new Error(response.status === 404 ? "המוסד לא נמצא." : "לא ניתן לטעון את הנתונים כרגע.");
  return (await response.json()) as T;
}

export const fetchIsraelFacility = (id: string) => getJson<IsraelFacilityPage>(`/api/il/facilities/${encodeURIComponent(id)}`);
export const fetchIsraelFacilities = (city?: string) =>
  getJson<IsraelFacilityListItem[]>(`/api/il/facilities${city ? `?city=${encodeURIComponent(city)}` : ""}`);

// ---------------------------------------------------------------------------
// Focused requests from a family to one facility.
// ---------------------------------------------------------------------------

export type InquiryRequest = {
  room_type: string;
  level: string;
  move_in: string;
  monthly_cap_ils: number | null;
  deposit_cap_ils: number | null;
  contact_name: string;
  contact_phone: string;
  note: string;
};

export type InquiryMessage = {
  from: "FAMILY" | "FACILITY";
  kind: "REQUEST" | "REPLY" | "ACCEPT" | "ALTERNATIVE" | "NEED_INFO" | "DECLINE";
  text?: string | null;
  monthly_ils?: number | null;
  deposit_ils?: number | null;
  at: string;
};

export type InquiryView = {
  inquiry_id: number;
  facility: { canonical_id: string; name: string };
  status: string;
  status_label: string;
  request: Record<string, string | number | null>;
  messages: InquiryMessage[];
  created_at: string | null;
  visit: VisitView | null;
};

export type VisitSlot = { date: string; part: "MORNING" | "NOON" | "AFTERNOON"; label?: string };
export type VisitView = {
  status: "REQUESTED" | "FACILITY_PROPOSED" | "CONFIRMED" | "CANCELLED";
  status_label: string;
  mode: "IN_PERSON" | "VIDEO";
  mode_label: string;
  visitors: number;
  note: string | null;
  slots: (VisitSlot & { label: string })[];
  confirmed: { date: string; time: string; note: string | null; label: string } | null;
};

async function sendJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = "";
    try {
      const parsed = (await response.json()) as { detail?: unknown };
      detail = typeof parsed.detail === "string" ? parsed.detail : "";
    } catch {
      detail = "";
    }
    throw new Error(detail || "השליחה נכשלה. נסו שוב.");
  }
  return (await response.json()) as T;
}

export const sendInquiry = (canonicalId: string, request: InquiryRequest) =>
  sendJson<{ token: string; link_path: string }>(`/api/il/facilities/${encodeURIComponent(canonicalId)}/inquiries`, request);
export const fetchInquiry = (token: string) => getJson<InquiryView>(`/api/il/inquiries/${encodeURIComponent(token)}`);
export const replyToInquiry = (token: string, text: string) =>
  sendJson<InquiryView>(`/api/il/inquiries/${encodeURIComponent(token)}/reply`, { text });

export const ROOM_LABELS: Record<string, string> = {
  SINGLE: "חדר ליחיד",
  SHARED_2: "חדר משותף לשניים",
  SHARED_3PLUS: "חדר לשלושה ומעלה",
  COUPLE_UNIT: "יחידה לבני זוג",
  STUDIO: "דירת חדר",
  APT_2: "דירת 2 חדרים",
  APT_3: "דירת 3 חדרים",
};
export const LEVEL_LABELS: Record<string, string> = {
  INDEPENDENT: "עצמאי/ת",
  FRAIL: "תשוש/ה",
  NURSING: "סיעודי/ת",
  COGNITIVE_FRAIL: "תשוש/ת נפש",
};
export const MOVE_IN_LABELS: Record<string, string> = {
  ASAP: "בהקדם",
  WITHIN_MONTH: "בתוך חודש",
  WITHIN_3_MONTHS: "בתוך שלושה חודשים",
  EXPLORING: "רק בודקים",
};
export const MESSAGE_LABELS: Record<InquiryMessage["kind"], string> = {
  REQUEST: "הבקשה נשלחה",
  REPLY: "תשובת המשפחה",
  ACCEPT: "המוסד מאשר שיש התאמה",
  ALTERNATIVE: "המוסד מציע מסלול אחר",
  NEED_INFO: "המוסד מבקש פרט נוסף",
  DECLINE: "המוסד לא יכול לקבל כרגע",
};

export type FeedbackSummary = {
  count: number;
  min_to_show: number;
  shown: boolean;
  aspects?: { key: string; label: string; average: number | null; answers: number }[];
  recommend_pct?: number;
  moved_in?: number;
};
export type FeedbackAnswer = {
  relation: "VISITED" | "MOVED_IN";
  ratings: Record<string, number>;
  recommend: "YES" | "NO";
  comment?: string | null;
};
export type FeedbackState = {
  form: { relations: { value: string; label: string }[]; aspects: { key: string; label: string }[]; scale: number[]; min_to_show: number };
  mine: FeedbackAnswer | null;
};
export const fetchFeedback = (token: string) => getJson<FeedbackState>(`/api/il/inquiries/${encodeURIComponent(token)}/feedback`);
export const sendFeedback = (token: string, answer: FeedbackAnswer) =>
  sendJson<FeedbackState>(`/api/il/inquiries/${encodeURIComponent(token)}/feedback`, answer);

export type IsraelKeyLabel = { key: string; label: string };
export type IsraelResultCard = {
  rank: number;
  canonical_id: string;
  name: string;
  facility_type: string | null;
  city: string | null;
  distance_km: number | null;
  musts_met: IsraelKeyLabel[];
  preferences_met: IsraelKeyLabel[];
  preferences_not_met: IsraelKeyLabel[];
  unknown: IsraelKeyLabel[];
  budget: { label: string | null; offer: string | null } | null;
  prices: { status: string; label: string | null; verified_at?: string | null; offers: { text: string; availability: string }[] };
  source: { basis: string; label: string; updated_at: string | null };
  rank_key: unknown[];
};
export type IsraelResults = {
  status: "OK" | "NEEDS_INPUT";
  missing?: string[];
  interpretation: { status: string; message?: string; clarification_question?: string | null; conflicts?: unknown[] };
  musts?: IsraelKeyLabel[];
  preferences?: IsraelKeyLabel[];
  funnel?: {
    universe: number;
    passed: number;
    pending: number;
    failed: number;
    shown: number;
    fail_reasons: (IsraelKeyLabel & { count: number })[];
    pending_reasons: (IsraelKeyLabel & { count: number })[];
  };
  results: IsraelResultCard[];
  oomniker?: { lines: string[]; actions: string[] };
};
export const fetchIsraelResults = (questionnaire_state: Record<string, unknown>, natural_language_query: string) =>
  sendJson<IsraelResults>("/api/il/recommendations", { questionnaire_state, natural_language_query, limit: 20 });

export const requestVisit = (token: string, body: { slots: VisitSlot[]; mode: string; visitors: number; note?: string }) =>
  sendJson<VisitView>(`/api/il/inquiries/${encodeURIComponent(token)}/visit`, body);
export const answerVisit = (token: string, action: "ACCEPT" | "CANCEL") =>
  sendJson<VisitView>(`/api/il/inquiries/${encodeURIComponent(token)}/visit/answer`, { action });
export const visitCalendarHref = (token: string) => `/api/backend/api/il/inquiries/${encodeURIComponent(token)}/visit.ics`;
