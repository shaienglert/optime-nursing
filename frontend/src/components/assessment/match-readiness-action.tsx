export function MatchReadinessAction({ ready, submitting, recommendationsReady, onActivate }: {
  ready: boolean;
  submitting: boolean;
  recommendationsReady: boolean;
  onActivate: () => void;
}) {
  if (!ready) return null;

  return (
    <div data-match-readiness-action className="mt-8">
      <button
        type="button"
        disabled={submitting}
        onClick={onActivate}
        className="mt-4 min-h-12 border-b-2 border-[#2f6f5e] pb-1 text-left text-lg font-semibold text-[#2f6f5e] transition hover:border-[#1f4f42] hover:text-[#1f4f42] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#2f6f5e] disabled:cursor-wait disabled:opacity-60"
      >
        {submitting ? "Comparing communities" : recommendationsReady ? "View the matches below" : "Find My Best Matches"}
      </button>
    </div>
  );
}