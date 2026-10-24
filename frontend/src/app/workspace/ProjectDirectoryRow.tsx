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
  const titleBlocked = closed && (archived || !explicitProjectClose);
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
  const state = archived ? "已归档 · 只读" : closed ? "已关闭 · 可安全复制" : current
    ? "当前项目" : item.operationalState === "open" ? "未关闭" : "关闭状态未确认";
  return <article className="directory-item" data-project-id={item.id}>
    <div className="directory-row-heading">
      <button className="directory-open" disabled={disabled || titleBlocked} aria-describedby={titleBlocked ? capabilityId : undefined} onClick={() => { setExpanded(false); onOpen(item); }}>
        <strong>{item.brief.title || "未命名项目"}</strong>
        <small>{state} · r{item.revision} · <time dateTime={item.updatedAt}>{formatUiTimestamp(item.updatedAt)}</time></small>
      </button>
      <div className="directory-actions">
        {archived ? <Button variant="primary" disabled={disabled} onClick={() => act("restore")}>恢复</Button>
          : closed ? <Button variant="primary" disabled={disabled || !explicitProjectClose} aria-describedby={!explicitProjectClose ? capabilityId : undefined} onClick={() => act("open")}>重新打开</Button>
          : current ? explicitProjectClose && <>
            <Button variant="primary" disabled={disabled || Boolean(activity)} aria-describedby={activity ? activityId : undefined} onClick={() => act("close")}>保存并关闭项目</Button>
            <Button variant="quiet" disabled={disabled} onClick={() => act("force_close")}>退出工作区</Button>
          </> : <Button variant="primary" disabled={disabled} onClick={() => { setExpanded(false); onOpen(item); }}>打开</Button>}
        <div className="directory-disclosure" ref={disclosure}>
          <button className="button quiet" ref={trigger} disabled={disabled} aria-expanded={expanded} aria-controls={panelId}
            aria-label={`更多 · ${item.brief.title || "未命名项目"}`} onClick={() => setExpanded(value => !value)}>更多</button>
          {expanded && <div id={panelId} className="directory-management" role="group" aria-label="项目管理">
            <Button variant="quiet" disabled={disabled} onClick={() => act("duplicate")}>复制简报与规范内容</Button>
            {!archived && !closed && <>
              <Button variant="quiet" disabled={disabled || Boolean(activity)} aria-describedby={activity ? activityId : undefined} onClick={() => act("archive")}>归档</Button>
              {!current && explicitProjectClose && <Button variant="quiet" disabled={disabled || Boolean(activity)} aria-describedby={activity ? activityId : undefined} onClick={() => act("close")}>关闭项目</Button>}
            </>}
            <Button variant="danger" disabled={disabled} onClick={() => act("delete")}>删除项目…</Button>
          </div>}
        </div>
      </div>
    </div>
    {titleBlocked && <p id={capabilityId} className="action-prerequisite directory-activity">{archived
      ? `此项目已归档且已关闭；请先恢复${explicitProjectClose ? "，再重新打开。" : "。当前后端未提供重新打开已关闭项目的能力。"}` : "当前后端未提供重新打开已关闭项目的能力。"}</p>}
    {activity && <p id={activityId} className="action-prerequisite directory-activity">{activity}；任务结束前不能归档或安全关闭。可打开项目查看进展。</p>}
    {children}
  </article>;
}
