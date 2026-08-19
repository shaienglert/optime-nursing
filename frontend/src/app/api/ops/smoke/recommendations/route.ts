import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_BASE = (
  process.env.BACKEND_PROXY_TARGET ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/$/, "");

const PERSONAS = {
  son84: {
    questionnaire_state: {
      relationship: "Dad",
      ageGroup: "80-84",
      assistanceLevel: "Needs assistance with bathing and dressing",
      memoryStatus: "No",
      budget: 6500,
      distanceFromFamily: "Balanced location",
    },
    natural_language_query:
      "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing, meals and medication. No dementia.",
    limit: 5,
  },
  self84: {
    questionnaire_state: {
      relationship: "Myself",
      ageGroup: "80-84",
      assistanceLevel: "Needs assistance with bathing and dressing",
      memoryStatus: "No",
      budget: 6500,
      distanceFromFamily: "Balanced location",
    },
    natural_language_query:
      "I am 84, recently widowed, live in Las Vegas, am mentally alert and mobile, and need help with bathing, dressing, meals and medication. No dementia.",
    limit: 5,
  },
} as const;

type PersonaKey = keyof typeof PERSONAS;

export async function GET(request: NextRequest) {
  const persona = (request.nextUrl.searchParams.get("persona") || "son84") as PersonaKey;
  if (!(persona in PERSONAS)) {
    return NextResponse.json(
      { error: "Unsupported smoke persona", supported: Object.keys(PERSONAS) },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(PERSONAS[persona]),
    cache: "no-store",
  });

  const raw = await response.text();
  let body: unknown;
  try {
    body = raw ? JSON.parse(raw) : {};
  } catch {
    body = { raw };
  }

  if (!response.ok) {
    return NextResponse.json(
      { error: "Production decision engine smoke request failed", backend_status: response.status, backend_body: body },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }

  return NextResponse.json(
    {
      smoke: true,
      persona,
      generated_at: new Date().toISOString(),
      backend: BACKEND_BASE,
      result: body,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
