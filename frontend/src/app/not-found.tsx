import Link from "next/link";

export default function NotFound() {
  return <main className="min-h-screen bg-canvas px-5 py-16 text-ink sm:px-8"><section className="oomnik-panel mx-auto max-w-2xl p-8 sm:p-12"><p className="text-base font-semibold text-forest">Let’s find your way back</p><h1 className="mt-4 text-4xl font-semibold">This page isn’t here.</h1><p className="mt-5 text-lg leading-8 text-muted">You can return to the home page or open your saved conversations to pick up where you left off.</p><div className="mt-8 flex flex-wrap gap-4"><Link href="/" className="inline-flex min-h-12 items-center rounded-xl bg-forest px-6 py-3 text-lg font-semibold text-white hover:bg-forest-hover">Back to home</Link><Link href="/workspace" className="inline-flex min-h-12 items-center rounded-xl border border-forest px-6 py-3 text-lg font-semibold text-forest">Saved conversations</Link></div></section></main>;
}
