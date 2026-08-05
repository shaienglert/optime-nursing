import type { ReactNode } from "react";

export function QuestionnaireShell({ children, eyebrow, title, description, aside, environment, actions }: { children: ReactNode; eyebrow: string; title: string; description: string; aside?: ReactNode; environment?: ReactNode; actions?: ReactNode }) {
  return (
    <main className="relative isolate min-h-[calc(100vh-4rem)] overflow-hidden bg-[#263c36] text-lg text-[#2d2a26]">
      {environment}
      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-10 sm:py-16">
        <section className="min-w-0 rounded-[28px] bg-[#fffdf8]/90 px-6 py-9 shadow-[0_30px_90px_rgba(15,29,24,0.3)] backdrop-blur-[12px] motion-reduce:bg-[#fffdf8] motion-reduce:backdrop-blur-none sm:px-12 sm:py-14 lg:max-w-4xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.08em] text-[#3d6f5e]">{eyebrow}</p>
            {actions}
          </div>
          <h1 className="mt-5 max-w-3xl font-serif text-4xl leading-[1.08] tracking-normal text-[#25231f] sm:text-6xl">{title}</h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-[#625d55]">{description}</p>
          {aside ? <div className="mt-8 border-y border-[#d8d5cd] py-5">{aside}</div> : null}
          <div className="mt-14 sm:mt-20">{children}</div>
        </section>
      </div>
    </main>
  );
}