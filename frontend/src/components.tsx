import { Children, cloneElement, isValidElement, useId, type HTMLAttributes, type PropsWithChildren, type ReactNode } from "react";
import type { ServerStageName } from "./types";
import { stageLabels } from "./model";

export function Button({ variant = "default", className = "", busy, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "danger" | "quiet"; busy?: boolean }) {
  return <button {...props} aria-busy={busy || undefined} className={`button ${variant} ${className}`.trim()} />;
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

export function RequiredMark() {
  return <span className="required-mark" aria-hidden="true"> *</span>;
}

export function Field({ label, hint, required, children }: PropsWithChildren<{ label: string; hint?: string; required?: boolean }>) {
  const id = useId();
  const labelId = `${id}-label`;
  const hintId = `${id}-hint`;
  const fieldChildren = Children.toArray(children);
  const controls = fieldChildren.filter((child) =>
    isValidElement<React.AriaAttributes & { id?: string }>(child)
    && ["input", "select", "textarea"].includes(String(child.type)));
  const control = controls.length === 1 && isValidElement<React.AriaAttributes & { id?: string }>(controls[0]) ? controls[0] : undefined;
  const controlId = control?.props.id || `${id}-control`;
  // Only a single native control owns this label. Helper text stays outside it,
  // and compound/custom children retain their own names inside a labelled group.
  const content = fieldChildren.map((child) => control && child === control ? cloneElement(control, {
    id: controlId,
    "aria-describedby": [control.props["aria-describedby"], hint ? hintId : undefined].filter(Boolean).join(" ") || undefined,
  }) : child);
  return <div className="field" role={control ? undefined : "group"} aria-labelledby={control ? undefined : labelId} aria-describedby={!control && hint ? hintId : undefined}>
    {control ? <label id={labelId} htmlFor={controlId}>{label}{required && <RequiredMark />}</label> : <span id={labelId}>{label}{required && <RequiredMark />}</span>}
    {content}{hint && <small id={hintId}>{hint}</small>}
  </div>;
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
