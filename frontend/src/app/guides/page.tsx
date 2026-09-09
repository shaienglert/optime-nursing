import type { Metadata } from "next";
import Link from "next/link";
import { PUBLIC_ARTICLES } from "@/content/public-market-content";

export const metadata: Metadata = { title: "Senior Living Guides", description: "Practical, evidence-first guides for families comparing senior living and nursing care in Las Vegas and Nevada.", alternates: { canonical: "/guides" } };

export default function GuidesPage() {
  return <main className="min-h-screen bg-[#f8f5ef] text-[#21312b]"><section className="border-b border-[#dbe4df] bg-[#edf6f1]"><div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#3a7969]">For families</p><h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">Senior living guides</h1><p className="mt-5 max-w-3xl text-lg leading-8 text-[#52645d]">Useful decisions require more than a directory listing. These guides explain what to verify and what to ask.</p></div></section><section className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12"><div className="grid gap-6 md:grid-cols-3">{PUBLIC_ARTICLES.map((article) => <article key={article.slug} className="flex flex-col rounded-3xl border border-[#d8e7e1] bg-white p-7 shadow-sm"><p className="text-xs font-semibold uppercase tracking-[0.15em] text-[#3a7969]">{article.readingTime}</p><h2 className="mt-4 text-2xl font-semibold tracking-[-0.03em]">{article.title}</h2><p className="mt-4 flex-1 leading-7 text-[#52645d]">{article.description}</p><Link href={`/guides/${article.slug}`} className="mt-7 text-sm font-semibold text-[#285f51] underline underline-offset-4">Read the guide →</Link></article>)}</div></section></main>;
}
