import type { HTMLAttributes, PropsWithChildren, ReactNode } from "react";
import type { ServerStageName } from "./types";
import { stageLabels } from "./model";

export function Button({ variant = "default", className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "danger" | "quiet" }) {
  return <button {...props} className={`button ${variant} ${className}`.trim()} />;
}

export function Panel({ children, className = "", ...props }: PropsWithChildren<HTMLAttributes<HTMLElement>>) {
  return <section {...props} className={`panel ${className}`.trim()}>{children}</section>;
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-header">
    <div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{description}</p></div>
    {actions && <div className="page-actions">{actions}</div>}
  </header>;
}

export function Badge({ tone = "neutral", children }: PropsWithChildren<{ tone?: "neutral" | "ok" | "warning" | "danger" | "accent" }>) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function EmptyState({ title, children }: PropsWithChildren<{ title: string }>) {
  return <div className="empty-state"><strong>{title}</strong><p>{children}</p></div>;
}

export function StageStatus({ staleStages, stage }: { staleStages: ServerStageName[]; stage: ServerStageName }) {
  return staleStages.includes(stage)
    ? <Badge tone="warning">{stageLabels[stage]}待重建</Badge>
    : <Badge tone="ok">{stageLabels[stage]}已同步</Badge>;
}

export function Field({ label, hint, children }: PropsWithChildren<{ label: string; hint?: string }>) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}

export function JsonPreview({ value }: { value: unknown }) {
  return <pre className="code-block" tabIndex={0}><code>{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</code></pre>;
}

export function ErrorNotice({ message }: { message: string }) {
  return <div className="notice error" role="alert"><strong>请求未完成</strong><span>{message}</span></div>;
}

export function Spinner({ label = "正在处理" }: { label?: string }) {
  return <span className="spinner" role="status"><i aria-hidden="true" />{label}</span>;
}
