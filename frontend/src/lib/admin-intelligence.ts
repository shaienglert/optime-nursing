import { getApiBaseUrl, joinApiUrl } from "@/lib/api";

export type CompetitiveIntelligenceSignal = {
  competitor_key: string;
  competitor_name: string;
  signal_type: string;
  source_url: string;
  detail_text: string;
  first_observed_at: string;
  last_observed_at: string;
  last_changed_at?: string | null;
};

export type MarketSupplySignal = {
  category: string;
  headline: string;
  snippet: string;
  city_state?: string | null;
  source_url: string;
  source_domain: string;
  first_observed_at: string;
};

export type MarketReportObservation = {
  segment: string;
  value: string;
  observed_period: string;
  source_name: string;
  source_url: string;
  evidence_status: string;
  source_scope: string;
};

export type MarketReportMetric = {
  metric_key: string;
  label: string;
  unit: string;
  scope: string;
  status: "AVAILABLE" | "MISSING";
  observations: MarketReportObservation[];
  reason?: string | null;
};

export type MarketIntelligenceReport = {
  geography_key: string;
  ranking_input: boolean;
  metrics: MarketReportMetric[];
};

async function fetchAdminJson<T>(path: string, adminToken: string): Promise<T> {
  const response = await fetch(joinApiUrl(getApiBaseUrl(), path), {
    headers: { "X-Admin-Token": adminToken },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Admin API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export function fetchCompetitiveIntelligenceSignals(adminToken: string): Promise<CompetitiveIntelligenceSignal[]> {
  return fetchAdminJson<CompetitiveIntelligenceSignal[]>("/competitive-intelligence/signals", adminToken);
}

export function fetchMarketSupplyIntelligenceSignals(adminToken: string): Promise<MarketSupplySignal[]> {
  return fetchAdminJson<MarketSupplySignal[]>("/market-supply-intelligence/signals", adminToken);
}

export function fetchMarketIntelligenceReport(adminToken: string): Promise<MarketIntelligenceReport> {
  return fetchAdminJson<MarketIntelligenceReport>("/market-intelligence/report?geography_key=NEVADA", adminToken);
}
