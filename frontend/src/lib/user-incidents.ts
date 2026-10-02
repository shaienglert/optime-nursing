export function reportClientIncident(kind: "CLIENT_RUNTIME_ERROR" | "UNHANDLED_REJECTION" | "API_FAILURE") {
  if (typeof window === "undefined") return;
  const allowed = ["/", "/intake", "/intake-confirmation", "/adaptive-interview", "/results", "/facilities", "/compare"];
  const page = allowed.find(p => window.location.pathname === p || (p !== "/" && window.location.pathname.startsWith(p + "/")));
  if (!page) return;
  // No error text, stack, request body, query, user ID or facility token.
  void fetch("/api/backend/api/user-incidents", { method: "POST", keepalive: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, page, event_id: crypto.randomUUID() }) }).catch(() => undefined);
}
