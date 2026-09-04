import { useState } from "react";
import type { ProjectBrief } from "../types";
import { Button, Field, PageHeader, Panel } from "../components";

export function BriefPage({ value, saving, onSave, onDraftChange }: { value: ProjectBrief; saving: boolean; onSave: (brief: ProjectBrief) => Promise<void>; onDraftChange?: (brief: ProjectBrief) => void }) {
  const [draft, setDraft] = useState(value);
  const set = <K extends keyof ProjectBrief>(key: K, next: ProjectBrief[K]) => setDraft((current) => {
    const updated = { ...current, [key]: next };
    onDraftChange?.(updated); return updated;
  });
  const numeric = <K extends keyof ProjectBrief>(key: K, raw: string) => set(key, Number(raw) as ProjectBrief[K]);
  return <div className="page">
    <PageHeader eyebrow="01 · Project contract" title="项目简报" description="先确定生成边界。所有下游阶段都引用这份版本化合同。" actions={<Button variant="primary" disabled={saving} onClick={() => void onSave(draft)}>{saving ? "保存中…" : "保存简报"}</Button>} />
    <div className="two-column wide-left">
      <Panel className="form-card">
        <div className="section-title"><span>叙事目标</span><strong>作品定义</strong></div>
        <Field label="片名"><input value={draft.title} onChange={(event) => set("title", event.target.value)} /></Field>
        <Field label="故事梗概"><textarea rows={5} value={draft.synopsis} onChange={(event) => set("synopsis", event.target.value)} /></Field>
        <div className="field-grid two">
          <Field label="类型"><input value={draft.genre || ""} onChange={(event) => set("genre", event.target.value)} /></Field>
          <Field label="视觉风格"><input value={draft.visualStyle || ""} onChange={(event) => set("visualStyle", event.target.value)} /></Field>
        </div>
        <div className="field-grid three">
          <Field label="语言"><select value={draft.language} onChange={(event) => set("language", event.target.value)}><option value="zh-CN">简体中文</option><option value="en-US">English</option></select></Field>
          <Field label="画幅"><select value={draft.aspectRatio} onChange={(event) => set("aspectRatio", event.target.value)}><option>16:9</option><option>9:16</option><option>1:1</option></select></Field>
          <Field label="目标游玩时长（秒）"><input type="number" min={30} max={3600} value={draft.targetPlaythroughSeconds} onChange={(event) => numeric("targetPlaythroughSeconds", event.target.value)} /></Field>
        </div>
      </Panel>
      <div className="stack">
        <Panel className="form-card">
          <div className="section-title"><span>DAG budget</span><strong>结构预算</strong></div>
          <div className="field-grid two">
            <Field label="每路径决定数"><input type="number" min={1} value={draft.decisionPointsPerPath} onChange={(event) => numeric("decisionPointsPerPath", event.target.value)} /></Field>
            <Field label="结局数"><input type="number" min={1} value={draft.endingCount} onChange={(event) => numeric("endingCount", event.target.value)} /></Field>
            <Field label="节点预算"><input type="number" min={3} value={draft.nodeBudget} onChange={(event) => numeric("nodeBudget", event.target.value)} /></Field>
            <Field label="最大出度"><input type="number" min={1} max={6} value={draft.maxOutDegree} onChange={(event) => numeric("maxOutDegree", event.target.value)} /></Field>
            <Field label="期望汇合数"><input type="number" min={0} value={draft.desiredJoinCount} onChange={(event) => numeric("desiredJoinCount", event.target.value)} /></Field>
          </div>
          <div className="range-summary"><span>每场分镜</span><strong>{draft.shotsPerSceneMin}–{draft.shotsPerSceneMax}</strong></div>
          <div className="field-grid two compact">
            <Field label="最少"><input type="number" min={1} value={draft.shotsPerSceneMin} onChange={(event) => numeric("shotsPerSceneMin", event.target.value)} /></Field>
            <Field label="最多"><input type="number" min={draft.shotsPerSceneMin} value={draft.shotsPerSceneMax} onChange={(event) => numeric("shotsPerSceneMax", event.target.value)} /></Field>
          </div>
        </Panel>
      </div>
    </div>
  </div>;
}
