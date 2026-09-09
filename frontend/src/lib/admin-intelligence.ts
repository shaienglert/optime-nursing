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
