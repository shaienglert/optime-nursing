"use client";

export default function FacilitiesError({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-4xl rounded-2xl border border-rose-200 bg-white p-6">
        <h1 className="text-xl font-semibold text-slate-900">Unable to load facilities</h1>
        <p className="mt-2 text-sm text-slate-600">{error.message}</p>
        <button
          type="button"
          onClick={reset}
          className="mt-4 rounded-full bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700"
        >
          Try again
        </button>
      </section>
    </main>
  );
}
