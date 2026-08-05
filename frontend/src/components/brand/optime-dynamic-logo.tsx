import Image from "next/image";

type OptimeDynamicLogoProps = {
  progress: number;
  ready: boolean;
};

export function OptimeDynamicLogo({ progress, ready }: OptimeDynamicLogoProps) {
  const normalizedProgress = Math.max(0, Math.min(100, progress));
  const isComplete = ready || normalizedProgress >= 99;
  const pulseClass = isComplete
    ? "shadow-[0_0_40px_rgba(90,166,43,0.20)]"
    : "shadow-[0_0_34px_rgba(90,166,43,0.14)]";

  return (
    <div className="rounded-2xl border border-[#d8e7e1] bg-[#f7fcfa] p-4">
      <div className="mx-auto flex w-full max-w-xl items-center justify-center">
        <div className={`rounded-[2rem] bg-white px-3 py-2 transition duration-500 ${pulseClass}`}>
          <Image
            src="/branding/optime-ai-logo.svg"
            alt="OPTIME AI Decision Engine"
            width={500}
            height={590}
            priority
            className="h-auto w-full max-w-[200px] animate-[optime-ai-logo-pulse_4.2s_ease-in-out_infinite]"
          />
        </div>
      </div>
    </div>
  );
}
