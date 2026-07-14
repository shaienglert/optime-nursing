import Link from "next/link";

export default function Home() {
  return (
    <main className="relative flex min-h-screen items-center bg-[radial-gradient(circle_at_20%_20%,#ecfeff_0%,#f8fafc_45%,#ffffff_100%)] px-6 py-14 sm:px-10 lg:px-16">
      <section className="mx-auto w-full max-w-5xl overflow-hidden rounded-3xl border border-cyan-100/80 bg-white/90 p-8 shadow-[0_20px_80px_-32px_rgba(14,116,144,0.45)] backdrop-blur sm:p-12">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700">
          OPTIME Nursing
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight text-slate-900 sm:text-5xl">
          Find the right home, not just the best-rated one.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-slate-600">
          Decision Intelligence for Senior Living
        </p>
        <div className="mt-10">
          <Link
            href="/facilities"
            className="inline-flex items-center rounded-full bg-cyan-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-cyan-800"
          >
            Search Facilities
          </Link>
        </div>
      </section>
    </main>
  );
}
