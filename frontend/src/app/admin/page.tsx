import Link from "next/link";

export default function AdminIndexPage() {
  return (
    <main className="min-h-screen bg-canvas px-6 py-8 text-ink sm:px-10 lg:px-16">
      <section className="mx-auto max-w-5xl space-y-6">
        <header>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-forest">Admin</p>
          <h1 className="mt-2 text-3xl font-semibold">OOmnik team workspace</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted">
            Everything the team needs to support families, follow up with communities and keep the information dependable.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          <Link href="/admin/client-followups" className="rounded-3xl border border-line bg-surface/80 p-6 hover:border-line">
            <h2 className="text-xl font-semibold">Client visits and pricing enquiries</h2>
            <p className="mt-2 text-sm text-muted">Follow up on saved requests, preferred visit dates, contact details and current room quotations.</p>
          </Link>
          <Link href="/admin/platform-operations" className="rounded-3xl border border-line bg-surface/80 p-6 hover:border-line">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Owner Operations</p>
            <h2 className="mt-2 text-xl font-semibold">Runtime, Supervisor, Knowledge</h2>
            <p className="mt-2 text-sm text-muted">Live runtime status, supervisor overview/incidents, and knowledge snapshot refresh/report visibility.</p>
          </Link>

          <Link href="/admin/executive-intelligence" className="rounded-3xl border border-line bg-surface/80 p-6 hover:border-line">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Executive Intelligence</p>
            <h2 className="mt-2 text-xl font-semibold">Daily Executive Report</h2>
            <p className="mt-2 text-sm text-muted">Existing control tower report history and authority-progress intelligence.</p>
          </Link>

          <Link href="/admin/facility-outreach" className="rounded-3xl border border-line bg-surface/80 p-6 hover:border-line">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Facility Outreach</p>
            <h2 className="mt-2 text-xl font-semibold">Requests Awaiting Approval</h2>
            <p className="mt-2 text-sm text-muted">Review and approve draft emails asking facilities for room types, pricing, and availability before they send.</p>
          </Link>

          <Link href="/partner-desk" className="rounded-3xl border border-forest/70 bg-forest/30 p-6 hover:border-forest">
            <p className="text-xs uppercase tracking-[0.2em] text-forest">Live Call Support</p>
            <h2 className="mt-2 text-xl font-semibold">Facility Sales Copilot</h2>
            <p className="mt-2 text-sm text-muted">Approved commercial answers, exact words to say, bridge phrases, disclosure protection, and escalation guidance.</p>
          </Link>
        </div>
      </section>
    </main>
  );
}
