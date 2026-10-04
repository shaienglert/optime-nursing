"use client";

import Link from "next/link";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="min-h-screen bg-canvas px-5 py-16 text-ink sm:px-8"><section className="oomnik-panel mx-auto max-w-2xl p-8 sm:p-12"><p className="text-base font-semibold text-forest">We’re here to help you continue</p><h1 className="mt-4 text-4xl font-semibold">Something interrupted this page.</h1><p className="mt-5 text-lg leading-8 text-muted">Try loading it again. If it still needs a moment, you can return to your saved conversations.</p><div className="mt-8 flex flex-wrap gap-4"><button type="button" onClick={reset} className="min-h-12 rounded-xl bg-forest px-6 py-3 text-lg font-semibold text-white hover:bg-forest-hover">Try again</button><Link href="/workspace" className="inline-flex min-h-12 items-center rounded-xl border border-forest px-6 py-3 text-lg font-semibold text-forest">Saved conversations</Link></div></section></main>;
}
