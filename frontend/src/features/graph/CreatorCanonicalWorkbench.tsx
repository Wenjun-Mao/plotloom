import { useEffect, useRef, useState } from "react";
import { PageHeader } from "../../components";
import type { WorkspaceProject } from "../../types";
import { GraphPreviewRecovery } from "./GraphPreviewRecovery";
import { CanonicalGraphCanvas } from "./CanonicalGraphCanvas";
import { CreatorCanonicalStoryInspector } from "./CreatorCanonicalStoryInspector";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { useCreatorGeometry } from "./useCreatorGeometry";
import { workspaceViewportTop } from "../../app/workspace/workspaceViewport";

export function creatorCanonicalSelectionGeometry(
  layoutRect: Pick<DOMRect, "top">,
  paneRect: Pick<DOMRect, "left">,
  paneClientLeft: number,
  paneClientWidth: number,
  currentScrollLeft: number,
  nodeRect: Pick<DOMRect, "top" | "height" | "left" | "right" | "width">,
) {
  const visibleLeft = paneRect.left + paneClientLeft;
  const visibleRight = visibleLeft + paneClientWidth;
  const nodeCenterX = nodeRect.left + nodeRect.width / 2;
  const viewportCenterX = visibleLeft + paneClientWidth / 2;
  return {
    selectedY: nodeRect.top + nodeRect.height / 2 - layoutRect.top,
    needsHorizontalReveal: nodeRect.left < visibleLeft || nodeRect.right > visibleRight,
    scrollLeft: currentScrollLeft + nodeCenterX - viewportCenterX,
  };
}

export function CreatorCanonicalWorkbench({ project, readOnlyReason }: { project: WorkspaceProject; readOnlyReason: string }) {
  const owner = useGraphWorkbench(), graph = project.storyGraph;
  const selectedNode = graph.nodes.find(node => node.id === owner.selectedNodeId)
    ?? graph.nodes.find(node => node.id === graph.startNodeId)
    ?? graph.nodes[0];
  const [selectedY, setSelectedY] = useState<number>();
  const geometry = useCreatorGeometry(project.id!, selectedY);
  const revealedSelection = useRef<string | null>(null);
  useEffect(() => {
    if (!selectedNode || !geometry.ready) { setSelectedY(undefined); return; }
    // Wait one paint after the geometry owner becomes ready so React Flow's
    // initial fitView transform is reflected in the node's rendered bounds.
    const frame = requestAnimationFrame(() => {
      const pane = geometry.chart.current;
      const layoutElement = geometry.layout.current;
      const element = [...(pane?.querySelectorAll<HTMLElement>(".canonical-flow-node") ?? [])].find(item => item.dataset.id === selectedNode.id);
      if (!pane || !layoutElement || !element) { setSelectedY(undefined); return; }
      const rect = element.getBoundingClientRect();
      const paneRect = pane.getBoundingClientRect();
      const selection = creatorCanonicalSelectionGeometry(
        layoutElement.getBoundingClientRect(), paneRect, pane.clientLeft, pane.clientWidth, pane.scrollLeft, rect,
      );
      setSelectedY(selection.selectedY);
      const top = workspaceViewportTop();
      const initialStoredPosition = revealedSelection.current === null && geometry.storedPosition.current;
      revealedSelection.current = selectedNode.id;
      if (initialStoredPosition) return;
      if (rect.top < top + 12 || rect.bottom > window.innerHeight - 12) window.scrollBy(0, (rect.top + rect.bottom - top - window.innerHeight) / 2);
      if (selection.needsHorizontalReveal) pane.scrollLeft = selection.scrollLeft;
    });
    return () => cancelAnimationFrame(frame);
  }, [graph, geometry.chartWidth, geometry.ready, selectedNode?.id]);

  const selectedId = selectedNode?.id ?? null;
  return <section className="page creator-workbench creator-canonical-workbench" data-testid="creator-workbench" data-read-only-canonical="true">
    <PageHeader eyebrow="故事 → 制作" title="创作工作台" description="已接受路线的创作视图：自动排列剧情，选择节点并在右侧阅读内容。当前规范图只读；不会从此处确认、应用或修改故事。" />
    <GraphPreviewRecovery />
    <p className="creator-desktop-boundary">桌面创作：浏览器窗口宽度至少 1280px；不支持手机或窄屏。</p>
    <p className="notice warning" role="status">{readOnlyReason}</p>
    <p className="creator-pan-hint">已接受路线 · {graph.nodes.length} 个节点 · {graph.edges.length} 条连接。图较宽时可在图内横向平移；向下滚动页面可查看后续剧情。</p>
    <div ref={geometry.layout} className="creator-layout">
      <div className="creator-chart-column">
        <CanonicalGraphCanvas value={graph} selectedNodeId={selectedId} onNodeSelect={owner.selectNode} scrollRef={geometry.chart} />
      </div>
      <div className="creator-divider-track">
        <div ref={geometry.divider} className="creator-divider" role="separator" tabIndex={0} aria-label="调整节点详情宽度" aria-orientation="vertical" aria-valuemin={300} aria-valuemax={520} aria-valuenow={300} {...geometry.dividerEvents}><span /></div>
      </div>
      <div className="creator-inspector-track">
        <aside ref={geometry.inspector} className="creator-inspector" aria-label="当前节点详情">
          <header><strong>{selectedNode?.title || "选择故事节点"}</strong><p>规范图只读 · 选择与布局仅保存在本浏览器</p></header>
          <div className="creator-inspector-body"><CreatorCanonicalStoryInspector graph={graph} nodeId={selectedId} /></div>
        </aside>
      </div>
    </div>
  </section>;
}
