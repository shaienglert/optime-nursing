import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

// Operational smoke routes execute real backend work. Fail closed if the
// frontend admin credential has not been configured.
export function requireOpsAuth(request: NextRequest): NextResponse | null {
  const expectedPassword = process.env.ADMIN_PASSWORD;
  const expectedUsername = process.env.ADMIN_USERNAME || "admin";
  if (!expectedPassword) {
    return NextResponse.json({ error: "Operations access is not configured" }, { status: 503 });
  }

  const header = request.headers.get("authorization");
  if (!header?.startsWith("Basic ")) {
    return NextResponse.json({ error: "Authentication required" }, {
      status: 401, headers: { "WWW-Authenticate": 'Basic realm="OOmnik Operations"' },
    });
  }

  try {
    const decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
    const separator = decoded.indexOf(":");
    if (separator < 0) throw new Error("Invalid credentials");
    const username = decoded.slice(0, separator);
    const password = decoded.slice(separator + 1);
    const supplied = Buffer.from(password);
    const expected = Buffer.from(expectedPassword);
    if (username !== expectedUsername || supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) {
      throw new Error("Invalid credentials");
    }
    return null;
  } catch {
    return NextResponse.json({ error: "Invalid credentials" }, {
      status: 401, headers: { "WWW-Authenticate": 'Basic realm="OOmnik Operations"' },
    });
  }
}
