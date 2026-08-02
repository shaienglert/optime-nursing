import type { ReactNode } from "react";

export function QuestionnaireShell({ children, eyebrow, title, description, aside }: { children: ReactNode; eyebrow: string; title: string; description: string; aside?: ReactNode }) {
  return (
    <main className="min-h-[calc(100vh-4rem)] bg-[#f7faf8] text-[#1f302b]">
      <div className={`mx-auto grid w-full gap-8 px-4 py-8 sm:px-8 sm:py-12 ${aside ? "max-w-6xl lg:grid-cols-[minmax(0,1fr)_280px]" : "max-w-3xl"}`}>
        <section className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#2f7867]">{eyebrow}</p>
          <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-[-0.03em] text-[#172b25] sm:text-4xl">{title}</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#526a62]">{description}</p>
          <div className="mt-8">{children}</div>
        </section>
        {aside ? <aside className="hidden border-l border-[#d9e5e0] pl-7 lg:block">{aside}</aside> : null}
      </div>
    </main>
  );
}