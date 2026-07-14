export type Facility = {
  id: number;
  cms_id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  phone: string | null;
  overall_rating: number | null;
  staffing_rating: number | null;
  quality_rating: number | null;
  inspection_rating: number | null;
  beds: number | null;
  latitude: number | null;
  longitude: number | null;
};

export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

export async function fetchFacilities(): Promise<Facility[]> {
  const response = await fetch(`${getApiBaseUrl()}/facilities`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load facilities (${response.status})`);
  }
  return (await response.json()) as Facility[];
}

export async function fetchFacilityById(id: string): Promise<Facility> {
  const response = await fetch(`${getApiBaseUrl()}/facilities/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load facility (${response.status})`);
  }
  return (await response.json()) as Facility;
}
