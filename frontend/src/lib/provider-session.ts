/**
 * The facility's portal session, opened from its personal OOMNIK link.
 * The backend takes the acting user from this token, never from the request body.
 */
export type ProviderSession = {
  session_token: string;
  facility_id: number;
  canonical_id: string;
  name: string;
  user_id: number;
};

const KEY = "optime_provider_session";

export function readProviderSession(): ProviderSession | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ProviderSession;
    return parsed?.session_token && parsed.facility_id ? parsed : null;
  } catch {
    return null;
  }
}

export function saveProviderSession(session: ProviderSession): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(session));
    window.dispatchEvent(new StorageEvent("storage", { key: KEY }));
  } catch {
    // Storage unavailable (private mode): the page still works for this visit only.
  }
}

export function clearProviderSession(): void {
  try {
    window.localStorage.removeItem(KEY);
    window.dispatchEvent(new StorageEvent("storage", { key: KEY }));
  } catch {
    // ignore
  }
}

export function providerAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const session = readProviderSession();
  return session ? { Authorization: `Bearer ${session.session_token}` } : {};
}

export function subscribeProviderSession(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

/** Stable snapshot for useSyncExternalStore (the raw string, parsed by the caller). */
export function providerSessionSnapshot(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}
