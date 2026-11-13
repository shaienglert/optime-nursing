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
