export function ProgressIndicator({ current, total, category }: { current: number; total: number; category: string }) {
  const progress = total ? Math.round((current / total) * 100) : 0;
  return (
    <div aria-label={`Assessment progress: ${progress}%`}>
      <div className="flex items-center justify-between gap-4 text-xs font-semibold text-[#557067]">
        <span>{category}</span><span>Step {current} of {total}</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#dfeae6]">
        <div className="h-full rounded-full bg-[#2f806d] transition-[width] duration-300" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-2 text-xs text-[#6d817a]">{progress}% complete. You can go back and change any answer.</p>
    </div>
  );
}