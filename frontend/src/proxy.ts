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
 * Optional whole-site lock (used while a deployment shows synthetic data).
 * Active only when SITE_GATE_PASSWORD is set; the username is SITE_GATE_USERNAME or "oomnik".
 */
function siteGate(request: NextRequest): NextResponse | null {
  const expectedPassword = process.env.SITE_GATE_PASSWORD;
  if (!expectedPassword) return null;
  const expectedUsername = process.env.SITE_GATE_USERNAME || "oomnik";
  const authorization = request.headers.get("authorization");
  if (authorization?.startsWith("Basic ")) {
    try {
      const decoded = atob(authorization.slice(6));
      const separator = decoded.indexOf(":");
      if (separator >= 0 && decoded.slice(0, separator) === expectedUsername && decoded.slice(separator + 1) === expectedPassword) {
        return null;
      }
    } catch {
      // fall through to the challenge
    }
  }
  return new NextResponse("האתר בהכנה. הגישה בסיסמה בלבד.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="OOMNIK", charset="UTF-8"',
      "Cache-Control": "no-store",
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
}

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  const gated = siteGate(request);
  if (gated) return gated;

  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    return enforceAdminAuth(request);
  }

  // The Israeli deployment opens on the Hebrew intake instead of the US home page.
  if (pathname === "/" && process.env.OOMNIK_MARKET === "israel") {
    return NextResponse.redirect(new URL("/he", request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Every page and API route; static build assets are left out.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
