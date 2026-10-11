import type { PageId } from "./contracts";

/** Switch presentations through the existing guarded workspace navigation. */
export function WorkbenchViewSwitch({ activePage, disabled, onNavigate }: {
  activePage: PageId;
  disabled: boolean;
  onNavigate: (stage: "creator" | "graph") => void;
}) {
  return <div className="workbench-mode-switch" role="group" aria-label="同一剧情图的两种视图">
    <strong className="workbench-view-heading">同一剧情图 · 两种视图</strong>
    <button aria-pressed={activePage === "creator"} disabled={disabled} onClick={() => onNavigate("creator")}>创作工作台</button>
    <button aria-pressed={activePage === "graph"} disabled={disabled} onClick={() => onNavigate("graph")}>专业工作台</button>
    <span className="workbench-view-hint">共用图草稿，切换只改变视图。</span>
  </div>;
}
