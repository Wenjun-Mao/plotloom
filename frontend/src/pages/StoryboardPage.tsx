import { useEffect, useMemo, useState } from "react";
import type { ApprovalDecision, MediaTask, SceneBeatPlan, Shot, StoryGraph, Storyboard, StoryboardReview } from "../types";
import { plotloomApi } from "../api";
import { deriveRoutes, groupStoryboard } from "../model";
import { Badge, Button, EmptyState, Field, PageHeader, Panel } from "../components";

const shotSizes: Array<{ value: Shot["shotSize"]; label: string }> = [
  { value: "extreme_wide", label: "大远景" }, { value: "wide", label: "全景" }, { value: "full", label: "全身" }, { value: "medium", label: "中景" }, { value: "close_up", label: "近景" }, { value: "extreme_close_up", label: "特写" }, { value: "insert", label: "插入镜头" },
];

export function StoryboardPage({ graph, sceneBeats, value, stale, mediaTasks, saving, entityId, onEntitySelect, onSave, onDraftChange, projectId, revision, contentHash }: {
  graph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  value: Storyboard;
  stale: boolean;
  mediaTasks: Record<string, MediaTask>;
  saving: boolean;
  entityId?: string;
  onEntitySelect?: (entityId: string) => void;
  onSave: (storyboard: Storyboard) => Promise<void>;
  onDraftChange?: (storyboard: Storyboard) => void;
  projectId?: string;
  revision?: number;
  contentHash?: string | null;
}) {
  const [storyboard, setStoryboard] = useState(value);
  const routes = useMemo(() => deriveRoutes(graph), [graph]);
  const [routeId, setRouteId] = useState("");
  const [selectedShotId, setSelectedShotId] = useState(value.shots[0]?.id || "");
  useEffect(() => {
    if (entityId && storyboard.shots.some((shot) => shot.id === entityId)) setSelectedShotId(entityId);
    else if (!entityId) setSelectedShotId(storyboard.shots[0]?.id || "");
  }, [entityId, storyboard.shots]);
  const route = routes.find((candidate) => candidate.id === routeId);
  const visible = groupStoryboard(storyboard, sceneBeats, route);
  const selectedShot = storyboard.shots.find((shot) => shot.id === selectedShotId);
  const selectedImageTask = selectedShot ? mediaTasks[`${selectedShot.id}:image`] : undefined;
  const selectedVideoTask = selectedShot ? mediaTasks[`${selectedShot.id}:video`] : undefined;
  const [review, setReview] = useState<StoryboardReview | null>(null);
  const [reviewError, setReviewError] = useState("");
  const [reviewer, setReviewer] = useState("");
  useEffect(() => { if (!projectId) return; void plotloomApi.getStoryboardReview(projectId).then(setReview).catch(() => setReviewError("Review 服务暂不可用；不影响编辑。")); }, [projectId, revision, contentHash]);
  const decide = async (decision: ApprovalDecision["decision"]) => {
    if (!projectId || !contentHash || revision === undefined || !review?.gateEvaluation || !reviewer.trim()) return;
    const response = await plotloomApi.decideStoryboardApproval(projectId, { expectedRevision: revision, contentHash, decision, reviewer, gateSetVersion: review.gateEvaluation.gateSetVersion });
    setReview((current) => current ? { ...current, decisions: [...current.decisions, response], activeApproval: response.active ? response.decision : null } : current);
  };
  const patchShot = (id: string, patch: Partial<Shot>) => setStoryboard((current) => {
    const updated = { ...current, shots: current.shots.map((shot) => shot.id === id ? { ...shot, ...patch } : shot) };
    onDraftChange?.(updated); return updated;
  });
  return <div className="page">
    <PageHeader eyebrow="05 · Grouped production board" title="分镜工作台" description="按场景分组，按完整剧情路径审阅。每个媒体任务只作用于一个镜头。" actions={<><Field label="路径过滤"><select value={routeId} onChange={(event) => setRouteId(event.target.value)}><option value="">全部场景</option>{routes.map((item, index) => <option key={item.id} value={item.id}>路径 {index + 1} · {item.label}</option>)}</select></Field><Button variant="primary" disabled={saving} onClick={() => void onSave(storyboard)}>{saving ? "正在保存…" : "保存分镜"}</Button></>} />
    {stale && <div className="notice warning"><strong>分镜已过期</strong><span>上游合同发生变化。现有手工镜头仍保留；请审阅差异后从合适阶段重建。</span></div>}
    <div className="notice"><strong>媒体生产尚未开放</strong><span>现有媒体结果保持可读；新的图片或视频任务必须等待 Approval 与不可变 ProductionSnapshot 流程完成。</span></div>
    <div className="storyboard-layout">
      <div className="shot-groups">
        {!visible.length && <EmptyState title="这条路径没有分镜">切换到“全部场景”或先生成 storyboard 阶段。</EmptyState>}
        {visible.map((group, groupIndex) => <section className="shot-group" key={group.sceneId}>
          <header><div><span>{String(groupIndex + 1).padStart(2, "0")}</span><strong>{group.title}</strong></div><small>{group.shots.length} shots · node {group.storyNodeId}</small></header>
          <div className="shot-strip">
            {group.shots.map((shot) => {
              const imageTask = mediaTasks[`${shot.id}:image`];
              const videoTask = mediaTasks[`${shot.id}:video`];
              return <article key={shot.id} className={`shot-card ${shot.id === selectedShotId ? "selected" : ""}`} onClick={() => { setSelectedShotId(shot.id); onEntitySelect?.(shot.id); }}>
                <button className="shot-select" aria-label={`编辑镜头 ${shot.title}`} onClick={(event) => { event.stopPropagation(); setSelectedShotId(shot.id); onEntitySelect?.(shot.id); }}>
                  <div className="shot-frame">
                    {imageTask?.outputUri ? <img src={imageTask.outputUri} alt={`${shot.title} 生成关键帧`} /> : <span>{String(shot.order).padStart(2, "0")}</span>}
                    {stale && <Badge tone="warning">STALE</Badge>}
                  </div>
                  <div className="shot-copy"><strong>{shot.title}</strong><small>{shot.shotSize} · {shot.durationUnits} units</small><p>{shot.action}</p></div>
                </button>
                <div className="media-controls">
                  <Button variant="quiet" disabled>图片生产未就绪</Button>
                  <Button variant="quiet" disabled>视频生产未就绪</Button>
                </div>
              </article>;
            })}
          </div>
        </section>)}
      </div>
      <Panel className="shot-inspector">
        <div className="section-title"><span>Single shot</span><strong>{selectedShot?.title || "选择镜头"}</strong></div>
        {selectedShot && <>
          {stale && <div className="stale-reasons"><strong>上游已变化</strong><span>镜头内容保留；保存前请检查动作、连续性和节拍覆盖。</span></div>}
          <div className="field-grid two compact"><Field label="景别"><select value={selectedShot.shotSize} onChange={(event) => patchShot(selectedShot.id, { shotSize: event.target.value as Shot["shotSize"] })}>{shotSizes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></Field><Field label="时长（units）"><input type="number" min={1} value={selectedShot.durationUnits} onChange={(event) => patchShot(selectedShot.id, { durationUnits: Number(event.target.value) })} /></Field></div>
          <Field label="动作"><textarea rows={4} value={selectedShot.action} onChange={(event) => patchShot(selectedShot.id, { action: event.target.value })} /></Field>
          <Field label="对白 Cue IDs（逗号分隔）"><input value={(selectedShot.cueIds || []).join(", ")} onChange={(event) => patchShot(selectedShot.id, { cueIds: event.target.value.split(",").map((id) => id.trim()).filter(Boolean) })} /></Field>
          <Field label="音频计划"><textarea rows={3} value={JSON.stringify(selectedShot.audioPlan || { events: [] }, null, 2)} onChange={(event) => { try { patchShot(selectedShot.id, { audioPlan: JSON.parse(event.target.value) }); } catch { /* retain incomplete draft text until valid JSON */ } }} /></Field>
          <Field label="所需实体状态"><textarea rows={3} value={JSON.stringify(selectedShot.requiredEntityStates || [], null, 2)} onChange={(event) => { try { patchShot(selectedShot.id, { requiredEntityStates: JSON.parse(event.target.value) }); } catch { /* preserve current structured state */ } }} /></Field>
          <Field label="运镜"><textarea rows={2} value={selectedShot.cameraMovement} onChange={(event) => patchShot(selectedShot.id, { cameraMovement: event.target.value })} /></Field>
          <details className="prompt-details" open><summary>关键帧任务 Prompt</summary><textarea readOnly rows={8} value={selectedImageTask?.derivedPrompt || "生成任务启动后，服务端派生的 Prompt 会显示在这里。"} /></details>
          <details className="prompt-details"><summary>视频任务 Prompt</summary><textarea readOnly rows={8} value={selectedVideoTask?.derivedPrompt || "生成任务启动后，服务端派生的 Prompt 会显示在这里。"} /></details>
          {selectedVideoTask?.outputUri && <a className="output-link" href={selectedVideoTask.outputUri} target="_blank" rel="noreferrer">打开生成视频</a>}
        </>}
      </Panel>
      <Panel className="shot-inspector">
        <div className="section-title"><span>Review</span><strong>{review?.activeApproval ? "已批准" : "等待批准"}</strong></div>
        {reviewError && <div className="notice warning">{reviewError}</div>}
        {review?.gateEvaluation && <>{review.gateEvaluation.results.map((gate) => <div key={gate.id} className={`notice ${gate.status === "fail" ? "warning" : ""}`}><strong>{gate.status.toUpperCase()} · {gate.gateId}</strong><span>{gate.reason} {gate.entityPath.length ? `(${gate.entityPath.join(" › ")})` : ""}</span></div>)}
          <Field label="审核人"><input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></Field>
          <div className="button-row"><Button variant="primary" disabled={!reviewer.trim()} onClick={() => void decide("approve")}>批准当前分镜</Button><Button variant="quiet" disabled={!reviewer.trim()} onClick={() => void decide("revoke")}>撤销批准</Button></div>
        </>}
      </Panel>
    </div>
  </div>;
}
