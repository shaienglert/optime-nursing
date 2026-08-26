import type { NextConfig } from "next";

// /api/backend/* is served by app/api/backend/[...path]/route.ts, not a
// framework rewrite -- a rewrite to an external destination is bound by
// Vercel's routing-layer proxy timeout, which is shorter and not
// configurable, unlike a route handler's own `maxDuration`.
const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
};

export default nextConfig;
