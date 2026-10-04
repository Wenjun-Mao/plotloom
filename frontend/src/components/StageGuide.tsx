import type { PropsWithChildren, ReactNode } from "react";

/** Instruction only: stage owners supply readiness and guarded navigation. */
export function StageGuide({ title = "本步指引", children, next }: PropsWithChildren<{ title?: string; next?: ReactNode }>) {
  return <aside className="stage-guide" aria-label={title}>
    <div><strong>{title}</strong><div className="stage-guide-content">{children}</div></div>
    {next && <div className="stage-guide-next">{next}</div>}
  </aside>;
}
