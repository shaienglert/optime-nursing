import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const maxDuration = 300;

const BACKEND_BASE = (
  process.env.BACKEND_INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/+$/, "");

const CLIENT_TEXT =
  "My mother is 82 and is looking for senior living in Las Vegas. She is fully independent with bathing, dressing, toileting, transfers, medications, decision-making and memory. She has no memory concerns, does not need cognitive support, has no mobility limitation, and has no special medical or nursing needs. Her total monthly budget is up to $8,000.";

const QUESTIONNAIRE_STATE = {
  relationship: "My mother",
  ageGroup: "80-84",
  assistanceLevel: "Fully independent",
  memoryStatus: "No",
  budget: 8000,
  locationCity: "Las Vegas",
  state: "NV",
};

function modalities(row: any): string[] {
  const values = [row?.canonical_type, ...(row?.housing_modalities || [])]
    .map((value) => String(value || "UNKNOWN").toUpperCase())
    .filter(Boolean);
  return Array.from(new Set(values));
}

function isIndependentProduct(row: any): boolean {
  const values = new Set(modalities(row));
  return values.has("INDEPENDENT_LIVING") || values.has("LIFE_PLAN_CCRC");
}

function isSmallCareHome(row: any): boolean {
  const values = new Set(modalities(row));
  return values.has("ASSISTED_LIVING_RFG") && !values.has("INDEPENDENT_LIVING") && !values.has("LIFE_PLAN_CCRC");
}

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        questionnaire_state: QUESTIONNAIRE_STATE,
        natural_language_query: CLIENT_TEXT,
        limit: 10,
      }),
      cache: "no-store",
    });
    const raw = await response.text();
    if (!response.ok) {
      return NextResponse.json(
        { status: "FAIL", error: `Decision engine ${response.status}`, detail: raw.slice(0, 800) },
        { status: 502, headers: { "Cache-Control": "no-store" } },
      );
    }

    const payload = raw ? JSON.parse(raw) : {};
    const intelligence = payload?.decision_intelligence || payload?.patient_needs_profile?.decision_intelligence || {};
    const strategy = intelligence?.living_strategy || payload?.patient_needs_profile?.living_strategy || {};
    const rows = payload?.results || [];
    const top5 = rows.slice(0, 5).map((row: any) => ({
      name: row?.facility_name ?? null,
      canonicalType: row?.canonical_type ?? null,
      housingModalities: row?.housing_modalities ?? [],
      careSettingStatus: row?.care_setting_fit?.status ?? null,
      hardGate: row?.client_intent_fit?.hard_gate ?? null,
      independentProduct: isIndependentProduct(row),
      smallCareHome: isSmallCareHome(row),
    }));

    const independentCount = top5.filter((row: any) => row.independentProduct).length;
    const smallCareHomeCount = top5.filter((row: any) => row.smallCareHome).length;
    const leadingStrategies = (strategy?.strategy_candidates || [])
      .filter((row: any) => Number(row?.rank_hint ?? 99) <= 2)
      .map((row: any) => row?.strategy_id);

    const assertions = {
      reachedReady: intelligence?.human_intelligence?.decision_readiness === "READY" || intelligence?.decision_readiness === "READY",
      independentLivingRepresentedInTop5: independentCount >= 1,
      smallCareHomesDoNotDominateTop5: smallCareHomeCount <= 2,
      leadingStrategyRecognizesIndependentLiving: leadingStrategies.some((value: string) =>
        ["INDEPENDENT_LIVING", "LIFE_PLAN_CCRC", "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE"].includes(String(value || "")),
      ),
    };

    const passed = Object.values(assertions).every(Boolean);
    return NextResponse.json(
      {
        status: passed ? "PASS" : "FAIL",
        caseId: "GOLDEN-INDEPENDENT-LAS-VEGAS-82-8K",
        clientText: CLIENT_TEXT,
        decisionReadiness: intelligence?.human_intelligence?.decision_readiness ?? intelligence?.decision_readiness ?? null,
        decisionFinality: intelligence?.decision_finality ?? null,
        leadingStrategies,
        strategyUniverse: intelligence?.strategy_universe ?? null,
        resultCount: payload?.result_count ?? rows.length,
        top5,
        assertions,
      },
      { status: passed ? 200 : 409, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return NextResponse.json(
      { status: "FAIL", error: error instanceof Error ? error.message : String(error) },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
