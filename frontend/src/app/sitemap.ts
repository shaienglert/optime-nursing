import type { MetadataRoute } from "next";
import { PUBLIC_ARTICLES } from "@/content/public-market-content";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://optime-nursing.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/las-vegas-senior-living`,
      lastModified: new Date("2026-09-09"),
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/guides`,
      lastModified: new Date("2026-09-09"),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    ...PUBLIC_ARTICLES.map((article) => ({
      url: `${SITE_URL}/guides/${article.slug}`,
      lastModified: new Date(article.updatedAt),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
}
