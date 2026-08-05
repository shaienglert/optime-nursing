type OptimeDynamicLogoProps = {
  progress: number;
  ready: boolean;
};

export function OptimeDynamicLogo({ progress, ready }: OptimeDynamicLogoProps) {
  const pathWidth = `${Math.max(6, Math.min(100, progress))}%`;

  return (
    <div className="rounded-2xl border border-[#d8e7e1] bg-[#f7fcfa] p-4">
      <div className="mx-auto flex w-full max-w-xl items-center justify-center">
        <div className="relative h-28 w-72">
          <div className="absolute inset-0 rounded-[2rem] border border-[#cfe2db] bg-white" />

          <div className="absolute left-5 top-7 h-3 w-3 rounded-full bg-[#7fa9a0]" />

          <div className="absolute left-8 top-[38px] right-8 h-2 overflow-hidden rounded-full bg-[#dbeae5]">
            <div
              className={`h-full rounded-full bg-gradient-to-r from-[#64b49f] via-[#2f8f79] to-[#1f725f] ${ready ? "optime-path-pulse" : ""}`}
              style={{ width: pathWidth }}
            />
          </div>

          <div className="absolute right-8 top-7 flex h-4 w-4 items-center justify-center">
            <span className={`block h-0 w-0 border-y-[6px] border-l-[10px] border-y-transparent ${ready ? "border-l-[#2d8b73] optime-arrow-flash" : "border-l-[#86b6a8]"}`} />
          </div>

          <div
            className="absolute top-1/2 h-8 w-8 -translate-y-1/2 rounded-full border border-[#9ec3b8] bg-white shadow-[0_10px_22px_-14px_rgba(35,92,78,0.5)] optime-compass-drift"
            style={{ left: `calc(12% + (${Math.max(0, Math.min(100, progress))}% * 0.66))` }}
          >
            <svg viewBox="0 0 24 24" className="h-full w-full p-1.5" aria-hidden="true">
              <circle cx="12" cy="12" r="9" fill="none" stroke="#8dbcae" strokeWidth="1.5" />
              <path d="M12 5 L14.8 12 L12 19 L9.2 12 Z" fill="#2f8f79" />
              <circle cx="12" cy="12" r="1.6" fill="#1f6254" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
