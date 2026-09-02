import { useMemo, useState } from "react";
import type { MediaKind, MediaTask, SceneBeatPlan, Shot, StoryGraph, Storyboard } from "../types";
import { deriveRoutes, groupStoryboard } from "../model";
import { Badge, Button, EmptyState, Field, PageHeader, Panel, Spinner } from "../components";

const shotSizes: Array<{ value: Shot["shotSize"]; label: string }> = [
  { value: "extreme_wide", label: "大远景" }, { value: "wide", label: "全景" }, { value: "full", label: "全身" }, { value: "medium", label: "中景" }, { value: "close_up", label: "近景" }, { value: "extreme_close_up", label: "特写" }, { value: "insert", label: "插入镜头" },
];

export function StoryboardPage({ graph, sceneBeats, value, stale, mediaTasks, saving, onSave, onMedia }: {
  graph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  value: Storyboard;
  stale: boolean;
  mediaTasks: Record<string, MediaTask>;
  saving: boolean;
  onSave: (storyboard: Storyboard) => Promise<void>;
  onMedia: (shot: Shot, kind: MediaKind) => Promise<void>;
}) {
  const [storyboard, setStoryboard] = useState(value);
  const routes = useMemo(() => deriveRoutes(graph), [graph]);
  const [routeId, setRouteId] = useState("");
  const [selectedShotId, setSelectedShotId] = useState(value.shots[0]?.id || "");
  const route = routes.find((candidate) => candidate.id === routeId);
  const visible = groupStoryboard(storyboard, sceneBeats, route);
  const selectedShot = storyboard.shots.find((shot) => shot.id === selectedShotId);
  const selectedImageTask = selectedShot ? mediaTasks[`${selectedShot.id}:image`] : undefined;
  const selectedVideoTask = selectedShot ? mediaTasks[`${selectedShot.id}:video`] : undefined;
  const patchShot = (id: string, patch: Partial<Shot>) => setStoryboard((current) => ({ ...current, shots: current.shots.map((shot) => shot.id === id ? { ...shot, ...patch } : shot) }));
  return <div className="page">
    <PageHeader eyebrow="05 · Grouped production board" title="分镜工作台" description="按场景分组，按完整剧情路径审阅。每个媒体任务只作用于一个镜头。" actions={<><Field label="路径过滤"><select value={routeId} onChange={(event) => setRouteId(event.target.value)}><option value="">全部场景</option>{routes.map((item, index) => <option key={item.id} value={item.id}>路径 {index + 1} · {item.label}</option>)}</select></Field><Button variant="primary" disabled={saving} onClick={() => void onSave(storyboard)}>{saving ? "正在保存…" : "保存分镜"}</Button></>} />
    {stale && <div className="notice warning"><strong>分镜已过期</strong><span>上游合同发生变化。现有手工镜头仍保留；请审阅差异后从合适阶段重建。</span></div>}
    <div className="storyboard-layout">
      <div className="shot-groups">
        {!visible.length && <EmptyState title="这条路径没有分镜">切换到“全部场景”或先生成 storyboard 阶段。</EmptyState>}
        {visible.map((group, groupIndex) => <section className="shot-group" key={group.sceneId}>
          <header><div><span>{String(groupIndex + 1).padStart(2, "0")}</span><strong>{group.title}</strong></div><small>{group.shots.length} shots · node {group.storyNodeId}</small></header>
          <div className="shot-strip">
            {group.shots.map((shot) => {
              const imageTask = mediaTasks[`${shot.id}:image`];
              const videoTask = mediaTasks[`${shot.id}:video`];
              const mediaBusy = (task?: MediaTask) => task?.status === "running" || task?.status === "queued";
              return <article key={shot.id} className={`shot-card ${shot.id === selectedShotId ? "selected" : ""}`} onClick={() => setSelectedShotId(shot.id)}>
                <button className="shot-select" aria-label={`编辑镜头 ${shot.title}`} onClick={() => setSelectedShotId(shot.id)}>
                  <div className="shot-frame">
                    {imageTask?.outputUri ? <img src={imageTask.outputUri} alt={`${shot.title} 生成关键帧`} /> : <span>{String(shot.order).padStart(2, "0")}</span>}
                    {stale && <Badge tone="warning">STALE</Badge>}
                  </div>
                  <div className="shot-copy"><strong>{shot.title}</strong><small>{shot.shotSize} · {shot.durationSeconds}s</small><p>{shot.action}</p></div>
                </button>
                <div className="media-controls">
                  <Button variant="quiet" disabled={mediaBusy(imageTask)} onClick={(event) => { event.stopPropagation(); void onMedia(shot, "image"); }}>{mediaBusy(imageTask) ? <Spinner label="关键帧" /> : "生成关键帧"}</Button>
                  <Button variant="quiet" disabled={mediaBusy(videoTask)} onClick={(event) => { event.stopPropagation(); void onMedia(shot, "video"); }}>{mediaBusy(videoTask) ? <Spinner label="视频" /> : "生成视频"}</Button>
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
          <div className="field-grid two compact"><Field label="景别"><select value={selectedShot.shotSize} onChange={(event) => patchShot(selectedShot.id, { shotSize: event.target.value as Shot["shotSize"] })}>{shotSizes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></Field><Field label="时长"><input type="number" min={1} value={selectedShot.durationSeconds} onChange={(event) => patchShot(selectedShot.id, { durationSeconds: Number(event.target.value) })} /></Field></div>
          <Field label="动作"><textarea rows={4} value={selectedShot.action} onChange={(event) => patchShot(selectedShot.id, { action: event.target.value })} /></Field>
          <Field label="对白"><textarea rows={3} value={selectedShot.dialogue} onChange={(event) => patchShot(selectedShot.id, { dialogue: event.target.value })} /></Field>
          <Field label="运镜"><textarea rows={2} value={selectedShot.cameraMovement} onChange={(event) => patchShot(selectedShot.id, { cameraMovement: event.target.value })} /></Field>
          <details className="prompt-details" open><summary>关键帧任务 Prompt</summary><textarea readOnly rows={8} value={selectedImageTask?.derivedPrompt || "生成任务启动后，服务端派生的 Prompt 会显示在这里。"} /></details>
          <details className="prompt-details"><summary>视频任务 Prompt</summary><textarea readOnly rows={8} value={selectedVideoTask?.derivedPrompt || "生成任务启动后，服务端派生的 Prompt 会显示在这里。"} /></details>
          {selectedVideoTask?.outputUri && <a className="output-link" href={selectedVideoTask.outputUri} target="_blank" rel="noreferrer">打开生成视频</a>}
        </>}
      </Panel>
    </div>
  </div>;
}
