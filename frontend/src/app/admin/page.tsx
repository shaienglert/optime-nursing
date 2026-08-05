import Link from "next/link";

export default function AdminIndexPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-5xl space-y-6">
        <header>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-300">Admin</p>
          <h1 className="mt-2 text-3xl font-semibold">OPTIME Admin Surfaces</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-300">
            Access the existing operations and executive intelligence views without creating duplicate systems.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          <Link href="/admin/platform-operations" className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 hover:border-slate-600">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Owner Operations</p>
            <h2 className="mt-2 text-xl font-semibold">Runtime, Supervisor, Knowledge</h2>
            <p className="mt-2 text-sm text-slate-300">Live runtime status, supervisor overview/incidents, and knowledge snapshot refresh/report visibility.</p>
          </Link>

          <Link href="/admin/executive-intelligence" className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 hover:border-slate-600">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Executive Intelligence</p>
            <h2 className="mt-2 text-xl font-semibold">Daily Executive Report</h2>
            <p className="mt-2 text-sm text-slate-300">Existing control tower report history and authority-progress intelligence.</p>
          </Link>
        </div>
      </section>
    </main>
  );
}
