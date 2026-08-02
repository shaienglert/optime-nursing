export function AdvisorResponse({ children }: { children: string }) {
  return (
    <div className="border-l-2 border-[#72a994] bg-[#edf5f1] px-4 py-3 text-[15px] leading-6 text-[#36574c]">
      <span className="font-semibold text-[#1f5f50]">OPTIME</span>
      <p className="mt-1">{children}</p>
    </div>
  );
}