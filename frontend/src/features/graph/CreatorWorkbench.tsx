import { useEffect, useMemo, useRef, useState } from "react";
import { Button, PageHeader } from "../../components";
import type { SourceOutlineReviewState, WorkspaceProject } from "../../types";
import type { PageId } from "../../app/workspace/contracts";
import type { WorkspaceSourceReviewRead } from "../../app/workspace/useWorkspaceSourceReview";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { GraphSafetyNotice } from "./GraphSafetyNotice";
import { GraphPreviewRecovery } from "./GraphPreviewRecovery";
import { CanonicalGraphReader } from "./CanonicalGraphReader";
import { CreatorStoryInspector } from "./CreatorStoryInspector";
import { GraphCommandDialog } from "./GraphCommandDialog";
import { GraphDraftDiscard } from "./GraphDraftDiscard";
import { GraphWorkflowActions } from "./GraphWorkflowActions";
import { CreatorChart } from "./CreatorChart";
import { CreatorEditDialog, type CreatorEdit } from "./CreatorEditDialog";
import { creatorLayout, CARD_HEIGHT } from "./creatorLayout";
import { creatorStructure } from "./creatorStructure";
import { useCreatorGeometry } from "./useCreatorGeometry";
import { useWorkspaceProduction } from "./WorkspaceProductionContext";
import { CreatorProductionInspector } from "./CreatorProductionInspector";
import { creatorAdmission } from "./creatorAdmission";
import { workspaceViewportTop } from "../../app/workspace/workspaceViewport";

export type CreatorNavigate = (stage: PageId, hash?: string) => void;
type CreatorProps = { project: WorkspaceProject; readOnly: boolean; sourceReview: WorkspaceSourceReviewRead; onNavigate: CreatorNavigate; onOpenShot: (shotId: string) => void };
export function CreatorWorkbench({ project, readOnly, sourceReview, onNavigate, onOpenShot }: CreatorProps) {
  const owner = useGraphWorkbench();
  if (!project.id) return <section className="page"><PageHeader title="创作工作台" description="先保存项目简报，再建立来源与故事路线。" /><Button onClick={() => onNavigate("brief")}>返回项目简报</Button></section>;
  if (owner.state?.readOnlyReason) return <section className="page"><h1>创作工作台</h1><GraphPreviewRecovery /><p className="notice warning">{owner.state.readOnlyReason}</p><CanonicalGraphReader value={project.storyGraph} /></section>;
  if (!owner.draft || !owner.state) return <section className="page"><GraphPreviewRecovery /></section>;
  return <CreatorCanvas project={project} readOnly={readOnly} source={sourceReview.value} sourceError={sourceReview.error} onSourceRetry={sourceReview.refresh} onNavigate={onNavigate} onOpenShot={onOpenShot} />;
}

function CreatorCanvas({ project, readOnly, source, sourceError, onSourceRetry, onNavigate, onOpenShot }: Omit<CreatorProps, "sourceReview"> & { source: SourceOutlineReviewState | null; sourceError: string; onSourceRetry: WorkspaceSourceReviewRead["refresh"] }) {
  const owner = useGraphWorkbench(), draft = owner.draft!;
  const [action, setAction] = useState<CreatorEdit | null>(null), [tab, setTab] = useState<"story" | "production">("story");
  const [selectedY, setSelectedY] = useState<number>();
  const production = useWorkspaceProduction();
  const admission = creatorAdmission(draft, source, owner.state!.baseCanonicalRevision, production.data?.bridge);
  const geometry = useCreatorGeometry(project.id!, selectedY);
  const revealedSelection = useRef<string | null>(null);
  const layout = useMemo(() => creatorLayout(draft, geometry.chartWidth), [draft, geometry.chartWidth]);
  const structure = useMemo(() => creatorStructure(draft, project.brief), [draft, project.brief]);
  const section = draft.mapping.sections.find(section => section.sectionId === owner.selectedNodeId);
  const disabled = readOnly || owner.readStatus !== "ready" || owner.busy || owner.stale || !geometry.desktop;
  useEffect(() => {
    const element = geometry.layout.current?.querySelector<HTMLElement>(`[data-creator-node="${owner.selectedNodeId}"]`);
    if (!element) { setSelectedY(undefined); return; }
    const rect = element.getBoundingClientRect(), top = workspaceViewportTop();
    setSelectedY(rect.top - geometry.layout.current!.getBoundingClientRect().top + CARD_HEIGHT / 2);
    if (!geometry.ready) return;
    const initialStoredPosition = revealedSelection.current === null && geometry.storedPosition.current;
    revealedSelection.current = owner.selectedNodeId;
    if (initialStoredPosition) return;
    if (rect.top < top + 12 || rect.bottom > window.innerHeight - 12) window.scrollBy(0, (rect.top + rect.bottom - top - window.innerHeight) / 2);
    const pane = geometry.chart.current!, paneRect = pane.getBoundingClientRect();
    if (rect.left < paneRect.left || rect.right > paneRect.right) {
      const node = layout.nodes.find(node => node.id === owner.selectedNodeId)!;
      pane.scrollLeft = node.x + 194 / 2 - pane.clientWidth / 2;
    }
  }, [owner.selectedNodeId, layout.nodes.find(node => node.id === owner.selectedNodeId)?.rank, geometry.ready]);
  return <section className="page creator-workbench" data-testid="creator-workbench">
    <PageHeader eyebrow="故事 → 制作" title="创作工作台" description="同一剧情图的创作视图：自动排列剧情，检查路线并进入制作。与专业工作台共用图草稿；保存、确认、应用仍是三项独立操作。" />
    <div className="creator-toolbar">
      <Button onClick={() => onNavigate("source", "source")}>来源、分支建议与报告</Button><Button onClick={() => onNavigate("characters")}>角色</Button><Button onClick={() => onNavigate("source", "art")}>美术参考</Button><Button onClick={() => onNavigate("brief")}>项目简报与结构设置</Button>
      <Button disabled={disabled || !owner.canUndo} onClick={() => void owner.undo()}>撤销结构修改</Button><GraphDraftDiscard disabled={disabled} />
    </div>
    <p className="creator-desktop-boundary">桌面创作：浏览器窗口宽度至少 1280px；不支持手机或窄屏。{!geometry.desktop && "请扩大窗口后继续编辑。"}</p>
    {sourceError && <p className="notice warning" role="alert">无法读取来源与大纲：{sourceError}<Button onClick={() => void onSourceRetry()}>重新读取来源与大纲</Button></p>}
    <GraphPreviewRecovery />
    {owner.stale && <p className="notice warning">简报、来源或已确认规范已变化。当前图草稿仍保留。<Button disabled={owner.busy || owner.readStatus !== "ready"} onClick={() => void owner.recover()}>在当前版本恢复为新草稿</Button></p>}
    <details className="creator-structure-check"><summary>结构检查 · {structure.incomplete ? "未完成" : structure.mismatches.length ? "与简报目标不同" : "可进入内容确认"}</summary>
      <p>实际：{structure.actual.nodes} 节点 · {structure.actual.endings} 结局 · {structure.actual.joins} 汇合 · {structure.actual.routes}{structure.truncated ? "+" : ""} 条完整路线 · 每条路线 {structure.actual.choices.join(" / ") || "尚未完成"} 次选择。</p>
      <p>简报目标：节点上限 {project.brief.nodeBudget} · {project.brief.endingCount} 结局 · {project.brief.desiredJoinCount} 汇合 · 每次完整播放 {project.brief.decisionPointsPerPath} 次选择 · 最多 {Math.min(6, project.brief.maxOutDegree)} 个选项。</p>
      <p>{structure.actual.pending} 条待连接 · {structure.actual.detached} 个未接入节点。{structure.mismatches.join("；")}</p><p>实际结构与简报分别保留。修改目标请返回简报预览并确认；不会自动改图或提高容量。最终确认由当前来源与规范验证。</p>
    </details>
    <GraphWorkflowActions
      save={{ disabled, onClick: () => void owner.saveDraft() }}
      confirm={{ disabled: disabled || !source?.acceptedOutline || structure.incomplete || structure.mismatches.length > 0 || !production.data?.bridge, onClick: () => source && void owner.confirmMapping(source) }}
      apply={{ variant: "primary", disabled: disabled || admission.installBlocked, onClick: () => source && void owner.installMapping(source) }}
      status={admission.reason}
    />
    <div ref={geometry.layout} className="creator-layout">
      <div className="creator-chart-column"><p className="creator-pan-hint">图按连接自动排列；剧情图较宽时，可在图内横向平移。向下滚动页面可查看后续剧情。</p>
        <div ref={geometry.chart} className="creator-chart-scroll" tabIndex={0} aria-label="剧情图横向平移"><CreatorChart layout={layout} disabled={disabled} onEdit={setAction} /></div>
        {draft.mapping.topology.edges.some(edge => !edge.sourceNodeId || !edge.targetNodeId) && <details className="creator-pending"><summary>待连接关系 · {structure.actual.pending}</summary>{draft.mapping.topology.edges.filter(edge => !edge.sourceNodeId || !edge.targetNodeId).map(edge => <p key={edge.id}>{edge.id} · {edge.sourceNodeId || "待定起点"} → {edge.targetNodeId || "待定目标"}<Button disabled={disabled || !edge.sourceNodeId} onClick={() => setAction({ type: "connection", nodeId: edge.sourceNodeId!, endpoint: "target", edgeId: edge.id })}>连接目标</Button></p>)}<Button onClick={() => onNavigate("graph")}>专业工作台：保留的文字与效果</Button></details>}
      </div>
      <div className="creator-divider-track"><div ref={geometry.divider} className="creator-divider" role="separator" tabIndex={0} aria-label="调整节点详情宽度" aria-orientation="vertical" aria-valuemin={300} aria-valuemax={520} aria-valuenow={300} {...geometry.dividerEvents}><span /></div></div>
      <div className="creator-inspector-track"><aside ref={geometry.inspector} className="creator-inspector" aria-label="当前节点详情">
        <header><strong>{section?.title || "选择故事节点"}</strong><div className="creator-tabs" role="tablist"><button role="tab" aria-selected={tab === "story"} onClick={() => setTab("story")}>故事</button><button role="tab" aria-selected={tab === "production"} onClick={() => setTab("production")}>制作</button></div>{!action && <GraphSafetyNotice />}</header>
        <div className="creator-inspector-body"><CreatorStoryInspector projectId={project.id!} disabled={disabled} active={tab === "story"} onNavigate={onNavigate} />{tab === "production" && <CreatorProductionInspector project={project} read={production} graphCurrent={admission.graphCurrent} disabled={disabled} onNavigate={onNavigate} onOpenShot={onOpenShot} />}</div>
      </aside></div>
    </div>
    {action && <CreatorEditDialog action={action} onClose={() => setAction(null)} />}
    <GraphCommandDialog />
  </section>;
}
