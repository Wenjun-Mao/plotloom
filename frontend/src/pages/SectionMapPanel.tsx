import { useEffect, useState } from "react";
import { Button } from "../components";
import type { AcceptedOutlineRevision, AcceptedSectionMapRevision, SectionMap, SourceMapGraphAdmission } from "../types";
import type { StoryRoute } from "../model";

const blankMap = (): SectionMap => ({
  sections: [
    { sectionId: "opening", title: "开场", summary: "", ending: false },
    { sectionId: "ending-a", title: "结局 A", summary: "", ending: true },
    { sectionId: "ending-b", title: "结局 B", summary: "", ending: true },
  ],
  choice: {
    choiceId: "turn", sectionId: "opening", prompt: "", outcomes: [
      { outcomeId: "path-a", label: "", consequence: "", endingSectionId: "ending-a" },
      { outcomeId: "path-b", label: "", consequence: "", endingSectionId: "ending-b" },
    ],
  },
});

function cloneMap(mapping?: AcceptedSectionMapRevision): SectionMap {
  return mapping ? structuredClone(mapping.mapping) : blankMap();
}

export function SectionMapPanel({
  outline, accepted, status, staleReasons, graphAdmission, graphReady, sourceDirty, routes, readOnly, busy, onSave, onInstall, onContinue,
}: {
  outline: AcceptedOutlineRevision | null; accepted: AcceptedSectionMapRevision | null;
  status: "missing" | "current" | "stale"; staleReasons: string[]; graphAdmission: SourceMapGraphAdmission | null; graphReady: boolean; sourceDirty: boolean; routes: StoryRoute[]; readOnly: boolean; busy: boolean;
  onSave: (mapping: SectionMap) => void;
  onInstall: () => void;
  onContinue: () => void;
}) {
  const [mapping, setMapping] = useState<SectionMap>(() => cloneMap(accepted || undefined));
  useEffect(() => setMapping(cloneMap(accepted || undefined)), [accepted?.revision]);
  const updateSection = (index: number, key: "sectionId" | "title" | "summary", value: string) => {
    setMapping(current => ({ ...current, sections: current.sections.map((section, i) => i === index ? { ...section, [key]: value } : section) }));
  };
  const updateOutcome = (index: number, key: "outcomeId" | "label" | "consequence" | "endingSectionId", value: string) => {
    setMapping(current => ({ ...current, choice: { ...current.choice, outcomes: current.choice.outcomes.map((outcome, i) => i === index ? { ...outcome, [key]: value } : outcome) as SectionMap["choice"]["outcomes"] } }));
  };
  const endingSections = mapping.sections.filter(section => section.ending);
  const complete = Boolean(
    mapping.choice.choiceId.trim() && mapping.choice.prompt.trim() &&
    mapping.sections.every(section => section.sectionId.trim() && section.title.trim() && section.summary.trim()) &&
    mapping.choice.outcomes.every(outcome => outcome.outcomeId.trim() && outcome.label.trim() && outcome.consequence.trim() && outcome.endingSectionId),
  );
  const dirty = Boolean(accepted && JSON.stringify(mapping) !== JSON.stringify(accepted.mapping));
  const admissionMatchesMap = Boolean(
    accepted && graphAdmission?.status === "current"
    && graphAdmission.sectionMapRevision === accepted.revision
    && graphAdmission.sectionMapContentHash === accepted.contentHash,
  );
  const routeInstalled = status === "current" && admissionMatchesMap && graphReady;
  const applied = routeInstalled && !dirty;
  const saveDisabled = readOnly || busy || !complete || Boolean(accepted && !dirty && status !== "stale");
  const applyDisabled = readOnly || busy || !accepted || dirty || status !== "current" || applied;
  const continueDisabled = readOnly || busy || dirty || sourceDirty || !applied;

  return <article className="panel section-map" data-testid="section-map">
    <header><span>故事分支</span><strong>{status === "current" ? `当前 r${accepted?.revision}` : status === "stale" ? `需要重新检查 r${accepted?.revision}` : "尚未保存"}</strong></header>
    <p>在这里编辑故事章节和观众选择。保存不会自动生成剧本或视频；应用会创建或更新故事路线。当前支持一个选择、两个结局。</p>
    {status === "stale" && <div className="notice warning"><strong>故事分支需要重新检查</strong><span>{staleReasons.join("；") || "故事内容或已确认大纲已变化。请按当前大纲复核后另存。"}</span></div>}
    {!outline ? <p className="muted">先确认一个大纲，再建立章节与分支。</p> : <>
      <small>绑定来源 r{outline.sourceRevision} · outline r{outline.revision} · {outline.contentHash.slice(0, 12)}</small>
      <div className="section-map-sections">
        {mapping.sections.map((section, index) => <fieldset key={index}><legend>{section.ending ? `结局 ${index}` : "选择发生的章节"}</legend>
          <label>稳定章节 ID<input disabled={readOnly || busy || Boolean(accepted)} value={section.sectionId} onChange={event => updateSection(index, "sectionId", event.target.value)} /></label>
          <label>章节标题<input disabled={readOnly || busy} value={section.title} onChange={event => updateSection(index, "title", event.target.value)} /></label>
          <label>章节摘要<textarea disabled={readOnly || busy} value={section.summary} onChange={event => updateSection(index, "summary", event.target.value)} rows={3} /></label>
        </fieldset>)}
      </div>
      <fieldset className="section-map-choice"><legend>观众选择</legend>
        <label>选择 ID<input disabled={readOnly || busy || Boolean(accepted)} value={mapping.choice.choiceId} onChange={event => setMapping(current => ({ ...current, choice: { ...current.choice, choiceId: event.target.value } }))} /></label>
        <label>发生章节<select disabled={readOnly || busy || Boolean(accepted)} value={mapping.choice.sectionId} onChange={event => setMapping(current => ({ ...current, choice: { ...current.choice, sectionId: event.target.value } }))}>{mapping.sections.filter(section => !section.ending).map(section => <option key={section.sectionId} value={section.sectionId}>{section.title || section.sectionId}</option>)}</select></label>
        <label>选择问题<textarea disabled={readOnly || busy} value={mapping.choice.prompt} onChange={event => setMapping(current => ({ ...current, choice: { ...current.choice, prompt: event.target.value } }))} rows={2} /></label>
        {mapping.choice.outcomes.map((outcome, index) => <div className="section-map-outcome" key={index}><strong>路径 {index + 1}</strong>
          <label>路径 ID<input disabled={readOnly || busy || Boolean(accepted)} value={outcome.outcomeId} onChange={event => updateOutcome(index, "outcomeId", event.target.value)} /></label>
          <label>选项文字<input disabled={readOnly || busy} value={outcome.label} onChange={event => updateOutcome(index, "label", event.target.value)} /></label>
          <label>选择后的发展<textarea disabled={readOnly || busy} value={outcome.consequence} onChange={event => updateOutcome(index, "consequence", event.target.value)} rows={2} /></label>
          <label>对应结局<select disabled={readOnly || busy || Boolean(accepted)} value={outcome.endingSectionId} onChange={event => updateOutcome(index, "endingSectionId", event.target.value)}>{endingSections.map(section => <option key={section.sectionId} value={section.sectionId}>{section.title || section.sectionId}</option>)}</select></label>
        </div>)}
      </fieldset>
      <section className="section-map-actions" aria-label="故事分支操作">
        <div className="section-map-action">
          <div><strong>{accepted ? "保存修改" : "保存故事分支"}</strong><p>{status === "stale" ? "请重新确认当前内容并保存，以绑定最新故事内容和大纲。" : accepted ? "保存当前修改；未修改时无需再次保存。" : "保存章节、选项和对应结局；不会自动生成剧本或视频。"}</p></div>
          <Button variant={!accepted || dirty || status === "stale" ? "primary" : "quiet"} disabled={saveDisabled} onClick={() => onSave(mapping)}>{busy ? "正在保存…" : accepted ? "保存修改" : "保存故事分支"}</Button>
        </div>
        {accepted && <div className="section-map-action">
          <div><strong>应用到故事路线</strong><p>{dirty ? "请先保存修改，才能应用故事路线。" : status !== "current" ? "故事分支需要重新检查后才能应用。" : applied ? "当前故事路线已使用此版本，无需再次应用。" : "应用后将创建或更新故事路线，不会生成剧本或视频。更新现有路线后，后续内容可能需要重新检查。"}</p></div>
          <Button variant={!applyDisabled ? "primary" : "quiet"} disabled={applyDisabled} onClick={onInstall}>应用到故事路线</Button>
        </div>}
        {routeInstalled && <div className="section-map-action section-map-action-ready" data-testid="section-map-ready">
          <div><strong>{dirty ? "故事分支有未保存修改" : "故事路线已就绪"}</strong><p>{dirty ? "请先保存故事分支修改，再继续角色设定。" : sourceDirty ? "请先保存故事内容，再继续角色设定。" : "可继续完善角色设定；此操作不会生成内容或改动故事路线。"}</p></div>
          <Button variant="primary" disabled={continueDisabled} onClick={onContinue}>继续：角色设定</Button>
        </div>}
      </section>
      {graphAdmission && <small>故事路线 r{graphAdmission.graphRevision} · {graphAdmission.status === "current" ? "当前" : `需要重新检查：${graphAdmission.staleReasons.join("；")}`}</small>}
      {routes.length > 0 && <section className="section-map-routes" data-testid="section-map-route-cards"><strong>故事路线</strong>{routes.map((route, index) => <article key={route.id}><span>路径 {index + 1}</span><strong>{route.label}</strong><small>{route.nodeIds.join(" → ")}</small></article>)}</section>}
    </>}
  </article>;
}
