import { useState } from "react";
import type { Beat, ContinuityState, SceneBeatPlan } from "../types";
import { Button, Field, PageHeader, Panel } from "../components";

const emptyState = (note = ""): ContinuityState => ({
  facts: {},
  characterStates: {},
  propStates: {},
  locationState: null,
  screenDirection: null,
  lighting: null,
  sound: null,
  notes: note ? [note] : [],
});

export function SceneBeatsPage({ value, stale, saving, onSave }: { value: SceneBeatPlan; stale: boolean; saving: boolean; onSave: (value: SceneBeatPlan) => Promise<void> }) {
  const [plan, setPlan] = useState(value);
  const [selectedId, setSelectedId] = useState(value.scenes[0]?.id || "");
  const selected = plan.scenes.find((scene) => scene.id === selectedId);
  const beats = plan.beats.filter((beat) => beat.sceneId === selectedId).sort((left, right) => left.order - right.order);
  const updateBeat = (beatId: string, patch: Partial<Beat>) => setPlan((current) => ({ ...current, beats: current.beats.map((beat) => beat.id === beatId ? { ...beat, ...patch } : beat) }));
  const updateNotes = (beat: Beat, key: "entryState" | "exitState", note: string) => updateBeat(beat.id, { [key]: { ...beat[key], notes: note ? [note] : [] } });
  const addBeat = () => {
    if (!selected) return;
    const id = crypto.randomUUID();
    const next: Beat = { id, sceneId: selected.id, order: beats.length + 1, description: "", purpose: "", visibleEvent: "", dialogue: "", immediateResult: "", dramaticChange: "", entryState: emptyState(), exitState: emptyState(), continuityAnchors: [], continuityDelta: {} };
    setPlan((current) => ({ scenes: current.scenes.map((scene) => scene.id === selected.id ? { ...scene, beatIds: [...scene.beatIds, id] } : scene), beats: [...current.beats, next] }));
  };
  return <div className="page">
    <PageHeader eyebrow="04 · Scene decomposition" title="场景与节拍" description="每个剧情节点拆成可拍摄的原子事件；入口与出口连续性保持结构化合同。" actions={<><span className={`stage-chip ${stale ? "stale" : "ready"}`}>{stale ? "剧情图已变化" : `${plan.beats.length} 个节拍`}</span><Button variant="primary" disabled={saving} onClick={() => void onSave(plan)}>{saving ? "正在保存…" : "保存节拍"}</Button></>} />
    <div className="beats-layout">
      <nav className="scene-rail" aria-label="场景列表">
        {plan.scenes.map((scene, index) => <button key={scene.id} className={scene.id === selectedId ? "active" : ""} onClick={() => setSelectedId(scene.id)}><span>{String(index + 1).padStart(2, "0")}</span><strong>{scene.title}</strong><small>{plan.beats.filter((beat) => beat.sceneId === scene.id).length} beats</small></button>)}
      </nav>
      <div className="beat-editor">
        <div className="section-bar"><div><span className="eyebrow">Story node {selected?.storyNodeId}</span><h2>{selected?.title}</h2><small>{selected?.objective}</small></div><Button variant="quiet" onClick={addBeat}>＋ 添加节拍</Button></div>
        {beats.map((beat, index) => <Panel className="beat-card" key={beat.id}>
          <div className="beat-number"><span>BEAT</span><strong>{String(index + 1).padStart(2, "0")}</strong></div>
          <div className="beat-fields">
            <Field label="节拍描述"><textarea rows={3} value={beat.description} onChange={(event) => updateBeat(beat.id, { description: event.target.value })} /></Field>
            <Field label="当前镜头可见事件"><textarea rows={3} value={beat.visibleEvent} onChange={(event) => updateBeat(beat.id, { visibleEvent: event.target.value })} /></Field>
            <Field label="叙事目的"><textarea rows={2} value={beat.purpose} onChange={(event) => updateBeat(beat.id, { purpose: event.target.value })} /></Field>
            <div className="field-grid two compact"><Field label="入口连续性备注"><textarea rows={2} value={beat.entryState.notes.join("\n")} onChange={(event) => updateNotes(beat, "entryState", event.target.value)} /></Field><Field label="出口连续性备注"><textarea rows={2} value={beat.exitState.notes.join("\n")} onChange={(event) => updateNotes(beat, "exitState", event.target.value)} /></Field></div>
          </div>
        </Panel>)}
      </div>
    </div>
  </div>;
}
