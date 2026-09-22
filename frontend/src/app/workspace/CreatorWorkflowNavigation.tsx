import type { MouseEvent } from "react";

import type { PageId } from "./contracts";
import { sourceWorkflowHref, sourceWorkflowTarget, type SourceWorkflowTarget, viewHref, workspaceHref } from "./sourceWorkflowNavigation";

type WorkspaceDestination = { stage: PageId; hash?: string };

const destinations: Array<{ label: string; detail: string; destination: WorkspaceDestination; target?: SourceWorkflowTarget }> = [
  { label: "来源与大纲", detail: "来源、路线与接受", destination: { stage: "source", hash: "source" }, target: "source" },
  { label: "角色", detail: "文字与外观参考", destination: { stage: "characters" } },
  { label: "美术参考", detail: "环境与道具", destination: { stage: "source", hash: "art" }, target: "art" },
  { label: "剧本", detail: "当前剧本与阅读", destination: { stage: "source", hash: "script" }, target: "script" },
  { label: "分镜评审", detail: "只读评审证据", destination: { stage: "source", hash: "storyboard-review" }, target: "storyboard-review" },
];

function ordinaryNavigationClick(event: MouseEvent<HTMLAnchorElement>) {
  return event.button === 0 && !event.metaKey && !event.altKey && !event.ctrlKey && !event.shiftKey;
}

/** Links only to existing project-scoped owners; their panels retain readiness and next-action authority. */
export function CreatorWorkflowNavigation({ projectId, activePage, activeHash, disabled, onNavigate }: {
  projectId: string;
  activePage: PageId;
  activeHash: string;
  disabled: boolean;
  onNavigate: (destination: WorkspaceDestination) => void;
}) {
  const selectedSourceTarget = activePage === "source" ? sourceWorkflowTarget(activeHash) || "source" : "";
  if (!projectId) return <section className="creator-workflow-navigation unavailable" aria-label="创作流程"><strong>创作流程</strong><small>保存项目后，可在这里返回来源、角色和各项已接受的审阅工作。</small></section>;
  return <nav className="creator-workflow-navigation" aria-label="创作流程">
    <div className="creator-workflow-heading"><strong>创作流程</strong><small>每项状态和下一步都由对应工作区说明。</small></div>
    <div className="creator-workflow-links">
      {destinations.map((item) => {
        const active = item.target ? selectedSourceTarget === item.target : activePage === item.destination.stage;
        const href = item.target ? sourceWorkflowHref(projectId, item.target) : workspaceHref(projectId, item.destination.stage);
        return <a key={item.label} href={href} className={active ? "active" : ""} aria-current={active ? "step" : undefined} aria-disabled={disabled || undefined} onClick={(event) => {
          if (disabled) {
            event.preventDefault();
            return;
          }
          if (!ordinaryNavigationClick(event)) return;
          event.preventDefault();
          onNavigate(item.destination);
        }}><strong>{item.label}</strong><small>{item.detail}</small></a>;
      })}
      <a href={viewHref(projectId, "story-prototype")} target="_blank" rel="noreferrer" aria-disabled={disabled || undefined} onClick={(event) => { if (disabled) event.preventDefault(); }}><strong>阅读故事</strong><small>只读分支阅读</small></a>
      <a href={viewHref(projectId, "play")} target="_blank" rel="noreferrer" aria-disabled={disabled || undefined} onClick={(event) => { if (disabled) event.preventDefault(); }}><strong>播放故事</strong><small>只读播放视图</small></a>
    </div>
  </nav>;
}
