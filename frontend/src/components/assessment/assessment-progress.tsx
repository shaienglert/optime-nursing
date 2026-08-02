export function AssessmentProgress({ percentage, section, completed, required }: { percentage: number; section: string; completed: number; required: number }) {
  return (
    <div className="sticky top-16 z-20 -mx-4 border-y border-[#d7e4df] bg-[#f7faf8]/95 px-4 py-3 backdrop-blur sm:mx-0 sm:border sm:px-5">
      <div className="flex items-center justify-between gap-4 text-xs font-semibold text-[#46645a]">
        <span>{section}</span>
        <span>{percentage}% complete</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden bg-[#dce8e3]" aria-hidden="true">
        <div className="h-full bg-[#28725f] transition-[width] duration-500 motion-reduce:transition-none" style={{ width: `${percentage}%` }} />
      </div>
      <p className="mt-2 text-xs text-[#687b74]">{completed} of {required} required answers complete · Saved automatically</p>
    </div>
  );
}