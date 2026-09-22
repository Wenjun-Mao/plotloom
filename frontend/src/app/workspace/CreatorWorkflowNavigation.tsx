import type { MouseEvent } from "react";

import type { PageId } from "./contracts";
import { sourceWorkflowHref, sourceWorkflowTarget, type SourceWorkflowTarget, viewHref, workspaceHref } from "./sourceWorkflowNavigation";

type WorkspaceDestination = { stage: PageId; hash?: string };

const destinations: Array<{ label: string; destination: WorkspaceDestination; target?: SourceWorkflowTarget }> = [
  { label: "来源与大纲", destination: { stage: "source", hash: "source" }, target: "source" },
  { label: "角色", destination: { stage: "characters" } },
  { label: "美术参考", destination: { stage: "source", hash: "art" }, target: "art" },
  { label: "剧本", destination: { stage: "source", hash: "script" }, target: "script" },
  { label: "分镜评审", destination: { stage: "source", hash: "storyboard-review" }, target: "storyboard-review" },
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
    <div className="creator-workflow-heading"><strong>创作流程</strong></div>
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
        }}><strong>{item.label}</strong></a>;
      })}
      <a href={viewHref(projectId, "story-prototype")} target="_blank" rel="noreferrer" aria-disabled={disabled || undefined} onClick={(event) => { if (disabled) event.preventDefault(); }}><strong>阅读故事</strong></a>
      <a href={viewHref(projectId, "play")} target="_blank" rel="noreferrer" aria-disabled={disabled || undefined} onClick={(event) => { if (disabled) event.preventDefault(); }}><strong>播放故事</strong></a>
    </div>
  </nav>;
}
