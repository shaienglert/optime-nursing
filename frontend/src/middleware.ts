import { NextRequest, NextResponse } from "next/server";

function unauthorized(message = "Authentication required.") {
  return new NextResponse(message, {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="OPTIME Admin", charset="UTF-8"',
      "Cache-Control": "no-store",
    },
  });
}

export function middleware(request: NextRequest) {
  const expectedPassword = process.env.ADMIN_PASSWORD;
  const expectedUsername = process.env.ADMIN_USERNAME || "admin";

  // Fail closed: an admin surface must never become public because a secret was omitted.
  if (!expectedPassword) {
    return new NextResponse("Admin access is not configured.", {
      status: 503,
      headers: { "Cache-Control": "no-store" },
    });
  }

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Basic ")) {
    return unauthorized();
  }

  try {
    const decoded = atob(authorization.slice(6));
    const separator = decoded.indexOf(":");
    if (separator < 0) return unauthorized();

    const username = decoded.slice(0, separator);
    const password = decoded.slice(separator + 1);

    if (username !== expectedUsername || password !== expectedPassword) {
      return unauthorized("Invalid admin credentials.");
    }
  } catch {
    return unauthorized("Invalid admin credentials.");
  }

  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export const config = {
  matcher: ["/admin", "/admin/:path*"],
};
