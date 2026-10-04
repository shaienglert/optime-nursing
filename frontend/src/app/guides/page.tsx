import type { Metadata } from "next";
import Link from "next/link";
import { PUBLIC_ARTICLES } from "@/content/public-market-content";

export const metadata: Metadata = { title: "Senior Living Guides", description: "Practical, evidence-first guides for families comparing senior living and nursing care in Las Vegas and Nevada.", alternates: { canonical: "/guides" } };

export default function GuidesPage() {
  return <main className="min-h-screen bg-canvas text-ink"><section className="border-b border-line bg-sand"><div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-forest">For families</p><h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">A little clarity for your next step</h1><p className="mt-5 max-w-3xl text-lg leading-8 text-muted">Take your time. These guides help you understand your options, know what to ask and feel more prepared for the conversations ahead.</p></div></section><section className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12"><div className="grid gap-6 md:grid-cols-3">{PUBLIC_ARTICLES.map((article) => <article key={article.slug} className="flex flex-col rounded-3xl border border-line bg-white p-7 shadow-sm oomnik-panel"><p className="text-xs font-semibold uppercase tracking-[0.15em] text-forest">{article.readingTime}</p><h2 className="mt-4 text-2xl font-semibold tracking-[-0.03em]">{article.title}</h2><p className="mt-4 flex-1 leading-7 text-muted">{article.description}</p><Link href={`/guides/${article.slug}`} className="mt-7 text-sm font-semibold text-forest underline underline-offset-4">Read the guide →</Link></article>)}</div></section></main>;
}
