import { NextRequest, NextResponse } from "next/server";

function adminUnauthorized(message = "Authentication required.") {
  return new NextResponse(message, {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="OPTIME Admin", charset="UTF-8"',
      "Cache-Control": "no-store",
    },
  });
}

function enforceAdminAuth(request: NextRequest) {
  const expectedPassword = process.env.ADMIN_PASSWORD;
  const expectedUsername = process.env.ADMIN_USERNAME || "admin";

  if (!expectedPassword) {
    return new NextResponse("Admin access is not configured.", {
      status: 503,
      headers: { "Cache-Control": "no-store" },
    });
  }

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Basic ")) {
    return adminUnauthorized();
  }

  try {
    const decoded = atob(authorization.slice(6));
    const separator = decoded.indexOf(":");
    if (separator < 0) return adminUnauthorized();

    const username = decoded.slice(0, separator);
    const password = decoded.slice(separator + 1);

    if (username !== expectedUsername || password !== expectedPassword) {
      return adminUnauthorized("Invalid admin credentials.");
    }
  } catch {
    return adminUnauthorized("Invalid admin credentials.");
  }

  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store");
  return response;
}

/**
 * The legacy /intake questionnaire is no longer a production interview surface.
 * Client-intent clarification belongs to the governed Semantic AI interview.
 * Keep the route as a compatibility entry point for old bookmarks/sessions, but
 * never render the fixed questionnaire.
 */
export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    return enforceAdminAuth(request);
  }

  if (pathname === "/intake") {
    const target = new URL("/adaptive-interview", request.url);
    target.searchParams.set("next", "/results");
    return NextResponse.redirect(target);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin", "/admin/:path*", "/intake"],
};
