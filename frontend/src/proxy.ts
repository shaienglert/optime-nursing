import { NextRequest, NextResponse } from "next/server";

/**
 * The legacy /intake questionnaire is no longer a production interview surface.
 * Client-intent clarification belongs to the governed Semantic AI interview.
 * Keep the route as a compatibility entry point for old bookmarks/sessions, but
 * never render the fixed questionnaire.
 */
export function proxy(request: NextRequest) {
  const target = new URL("/adaptive-interview", request.url);
  target.searchParams.set("next", "/results");
  return NextResponse.redirect(target);
}

export const config = {
  matcher: ["/intake"],
};
