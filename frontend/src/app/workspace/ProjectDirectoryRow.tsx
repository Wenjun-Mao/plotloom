import { useEffect, useId, useRef, useState } from "react";
import { Button } from "../../components";
import type { ProjectListItem } from "../../types";
import { formatUiTimestamp } from "../../ui-time";
import type { LifecycleAction } from "./useProjectLifecycle";

/** A directory summary exposes positive run facts, never complete idle admission. */
export function ProjectDirectoryRow({ item, current, disabled, explicitProjectClose, onOpen, onAction, children }: {
  item: ProjectListItem; current: boolean; disabled: boolean; explicitProjectClose: boolean;
  onOpen: (item: ProjectListItem) => void;
  onAction: (item: ProjectListItem, action: LifecycleAction) => Promise<void>;
  children?: React.ReactNode;
}) {
  const archived = item.lifecycleStatus === "archived" || Boolean(item.archivedAt);
  const closed = item.operationalState === "closed";
  const runStatus = item.latestRun?.status;
  const activity = runStatus === "queued" ? "最近任务正在排队" : runStatus === "running"
    ? "最近任务正在运行" : runStatus === "cancel_requested" ? "最近任务正在等待取消" : "";
  const [expanded, setExpanded] = useState(false);
  const disclosure = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const activityId = useId();
  const capabilityId = useId();
  const titleBlocked = false;
  const restoreFocus = useRef(false);
  const focusOwner = useRef({ id: item.id, current });
  useEffect(() => {
    if (focusOwner.current.id !== item.id || focusOwner.current.current !== current) {
      restoreFocus.current = false;
      focusOwner.current = { id: item.id, current };
    }
    if (disabled) restoreFocus.current ||= Boolean(disclosure.current?.contains(document.activeElement));
    else if (restoreFocus.current) {
      if (document.activeElement === document.body || disclosure.current?.contains(document.activeElement)) trigger.current?.focus();
      restoreFocus.current = false;
    }
    setExpanded(false);
  }, [item.id, current, disabled, archived, closed, item.revision, item.lifecycleRevision, item.updatedAt, runStatus]);
  useEffect(() => {
    if (!expanded) return;
    const outside = (event: Event) => {
      if (!disclosure.current?.contains(event.target as Node)) setExpanded(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault(); event.stopImmediatePropagation();
      setExpanded(false); trigger.current?.focus();
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", outside);
    document.addEventListener("keydown", escape, true);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("focusin", outside);
      document.removeEventListener("keydown", escape, true);
    };
  }, [expanded]);
  const act = (action: LifecycleAction) => {
    setExpanded(false);
    trigger.current?.focus();
    restoreFocus.current = true;
    void onAction(item, action);
  };
  const state = [current ? "当前项目" : "", archived ? "已归档 · 只读" : "", closed ? "已冻结 · 只读" : ""].filter(Boolean).join(" · ");
  return <article className="directory-item" data-project-id={item.id}>
    <div className="directory-row-heading">
      <button className="directory-open" disabled={disabled || titleBlocked} aria-describedby={titleBlocked ? capabilityId : undefined} onClick={() => { setExpanded(false); onOpen(item); }}>
        <strong>{item.brief.title || "未命名项目"}</strong>
        <small>{state ? `${state} · ` : ""}r{item.revision} · <time dateTime={item.updatedAt}>{formatUiTimestamp(item.updatedAt)}</time></small>
      </button>
      <div className="directory-actions">
        {archived && <Button variant="primary" disabled={disabled} onClick={() => act("restore")}>恢复</Button>}
        {!current && <Button variant="primary" disabled={disabled} onClick={() => { setExpanded(false); onOpen(item); }}>打开</Button>}
        <div className="directory-disclosure" ref={disclosure}>
          <button className="button quiet" ref={trigger} disabled={disabled} aria-expanded={expanded} aria-controls={panelId}
            aria-label={`更多 · ${item.brief.title || "未命名项目"}`} onClick={() => setExpanded(value => !value)}>更多</button>
          {expanded && <div id={panelId} className="directory-management" role="group" aria-label="项目管理">
            <Button variant="quiet" disabled={disabled} onClick={() => act("duplicate")}>复制简报与规范内容</Button>
            {explicitProjectClose && <Button variant="quiet" disabled={disabled || (!closed && Boolean(activity))} onClick={() => act(closed ? "unfreeze" : "freeze")}>{closed ? "解除冻结" : "冻结项目"}</Button>}
            {!archived && <Button variant="quiet" disabled={disabled || Boolean(activity)} onClick={() => act("archive")}>归档</Button>}
            <Button variant="danger" disabled={disabled} onClick={() => act("delete")}>删除项目…</Button>
          </div>}
        </div>
      </div>
    </div>
    {activity && <p id={activityId} className="action-prerequisite directory-activity">{activity}；任务结束前不能归档或冻结。可打开项目查看进展。</p>}
    {children}
  </article>;
}
