import { getApiBaseUrl, joinApiUrl } from "@/lib/api";

/**
 * Client for the provider-facing portal.
 *
 * Kept out of api.ts deliberately: everything there serves the family side, and the two
 * audiences have different shapes -- families read, providers write. Sharing the base-URL
 * resolution keeps them consistent about where the backend lives without merging the two
 * surfaces into one module.
 */

export type AnswerState = "YES" | "NO" | "LIMITED" | "UNKNOWN";

export type ClaimSearchResult = {
  facility_id: number;
  cms_id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  beds: number | null;
  overall_rating: number | null;
  already_claimed: boolean;
};

export type PublicRecordField = {
  key: string;
  label: string;
  value: string | number | null;
  source: string;
};

export type ProfileQuestion = {
  key: string;
  label: string;
  value: AnswerState;
  source: string | null;
  updated_at: string | null;
};

export type ProfileSection = {
  section: string;
  edit_category: string;
  answered: number;
  total: number;
  questions: ProfileQuestion[];
};

export type ProfilePhoto = {
  id: number;
  category: string;
  url: string;
  caption: string | null;
  source: string;
  uploaded_at: string | null;
};

export type ProfileActivity = {
  category: string;
  availability: AnswerState;
  confidence: number;
  import_source: string | null;
  last_imported_at: string | null;
};

export type Completeness = {
  medical: number;
  lifestyle: number;
  dining: number;
  photos: number;
  activity: number;
  overall: number;
  photo_count: number;
  photo_target: number;
  unanswered_count: number;
  total_questions: number;
};

export type ProfileSnapshot = {
  facility_id: number;
  name: string;
  known_from_public_record: PublicRecordField[];
  sections: ProfileSection[];
  photos: ProfilePhoto[];
  photo_target: number;
  activities: ProfileActivity[];
  activity_calendar_connected: boolean;
  completeness: Completeness;
  answer_states: AnswerState[];
  governance: Record<string, boolean>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(joinApiUrl(getApiBaseUrl(), path), {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!response.ok) {
    // The backend answers a refused edit with a readable reason ("Role ACTIVITIES may not
    // answer Medical questions"). Surfacing that beats a status code the provider cannot act on.
    let detail = "";
    try {
      const body = (await response.json()) as { detail?: string };
      detail = typeof body?.detail === "string" ? body.detail : "";
    } catch {
      detail = "";
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function searchClaimableFacilities(
  query: string,
  options: { state?: string; city?: string } = {},
): Promise<ClaimSearchResult[]> {
  const params = new URLSearchParams({ q: query });
  if (options.state) params.set("state", options.state);
  if (options.city) params.set("city", options.city);
  return request<ClaimSearchResult[]>(`/provider/facilities/search?${params.toString()}`);
}

export async function fetchProfileSnapshot(facilityId: number): Promise<ProfileSnapshot> {
  return request<ProfileSnapshot>(`/provider/facilities/${facilityId}/profile`);
}

export async function saveCapabilities(
  facilityId: number,
  userId: number,
  answers: Record<string, AnswerState>,
): Promise<{ updated: number; unchanged: number; completeness: Completeness }> {
  return request(`/provider/facilities/${facilityId}/capabilities`, {
    method: "PUT",
    body: JSON.stringify({ user_id: userId, answers }),
  });
}

export async function addFacilityPhoto(
  facilityId: number,
  userId: number,
  photo: { url: string; category?: string; caption?: string },
): Promise<{ photo_id: number; completeness: Completeness }> {
  return request(`/provider/facilities/${facilityId}/photos`, {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      url: photo.url,
      category: photo.category || "general",
      caption: photo.caption || null,
    }),
  });
}

export async function removeFacilityPhoto(
  facilityId: number,
  userId: number,
  photoId: number,
): Promise<{ photo_id: number; removed: boolean; completeness: Completeness }> {
  return request(`/provider/facilities/${facilityId}/photos/${photoId}`, {
    method: "DELETE",
    body: JSON.stringify({ user_id: userId }),
  });
}

export function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}
