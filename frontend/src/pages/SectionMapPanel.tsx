import { useEffect, useState } from "react";
import { Button } from "../components";
import type { AcceptedOutlineRevision, AcceptedSectionMapRevision, SectionMap } from "../types";

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
  outline, accepted, status, staleReasons, readOnly, busy, onSave,
}: {
  outline: AcceptedOutlineRevision | null; accepted: AcceptedSectionMapRevision | null;
  status: "missing" | "current" | "stale"; staleReasons: string[]; readOnly: boolean; busy: boolean;
  onSave: (mapping: SectionMap) => void;
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

  return <article className="panel section-map" data-testid="section-map">
    <header><span>04 · Reviewed section map</span><strong>{status === "current" ? `当前 r${accepted?.revision}` : status === "stale" ? `过期 r${accepted?.revision}` : "尚未保存"}</strong></header>
    <p>这里是来源大纲的可编辑章节映射，不会生成或覆盖旧的 Bible / Graph。一个明确选择必须连到两个不同、已标记的结局。</p>
    {status === "stale" && <div className="notice warning"><strong>章节映射已过期</strong><span>{staleReasons.join("；") || "来源或已接受大纲已变化。请按当前大纲复核后另存。"}</span></div>}
    {!outline ? <p className="muted">先明确接受一个 outline，再建立章节与分支。</p> : <>
      <small>绑定来源 r{outline.sourceRevision} · outline r{outline.revision} · {outline.contentHash.slice(0, 12)}</small>
      <div className="section-map-sections">
        {mapping.sections.map((section, index) => <fieldset key={index}><legend>{section.ending ? `结局 ${index - 1}` : "选择发生的章节"}</legend>
          <label>稳定章节 ID<input disabled={readOnly || busy} value={section.sectionId} onChange={event => updateSection(index, "sectionId", event.target.value)} /></label>
          <label>章节标题<input disabled={readOnly || busy} value={section.title} onChange={event => updateSection(index, "title", event.target.value)} /></label>
          <label>章节摘要<textarea disabled={readOnly || busy} value={section.summary} onChange={event => updateSection(index, "summary", event.target.value)} rows={3} /></label>
        </fieldset>)}
      </div>
      <fieldset className="section-map-choice"><legend>唯一明确选择</legend>
        <label>选择 ID<input disabled={readOnly || busy} value={mapping.choice.choiceId} onChange={event => setMapping(current => ({ ...current, choice: { ...current.choice, choiceId: event.target.value } }))} /></label>
        <label>发生章节<select disabled={readOnly || busy} value={mapping.choice.sectionId} onChange={event => setMapping(current => ({ ...current, choice: { ...current.choice, sectionId: event.target.value } }))}>{mapping.sections.filter(section => !section.ending).map(section => <option key={section.sectionId} value={section.sectionId}>{section.title || section.sectionId}</option>)}</select></label>
        <label>选择问题<textarea disabled={readOnly || busy} value={mapping.choice.prompt} onChange={event => setMapping(current => ({ ...current, choice: { ...current.choice, prompt: event.target.value } }))} rows={2} /></label>
        {mapping.choice.outcomes.map((outcome, index) => <div className="section-map-outcome" key={index}><strong>路径 {index + 1}</strong>
          <label>路径 ID<input disabled={readOnly || busy} value={outcome.outcomeId} onChange={event => updateOutcome(index, "outcomeId", event.target.value)} /></label>
          <label>选择标签<input disabled={readOnly || busy} value={outcome.label} onChange={event => updateOutcome(index, "label", event.target.value)} /></label>
          <label>后果<textarea disabled={readOnly || busy} value={outcome.consequence} onChange={event => updateOutcome(index, "consequence", event.target.value)} rows={2} /></label>
          <label>抵达结局<select disabled={readOnly || busy} value={outcome.endingSectionId} onChange={event => updateOutcome(index, "endingSectionId", event.target.value)}>{endingSections.map(section => <option key={section.sectionId} value={section.sectionId}>{section.title || section.sectionId}</option>)}</select></label>
        </div>)}
      </fieldset>
      <Button variant="primary" disabled={readOnly || busy || !complete} onClick={() => onSave(mapping)}>{busy ? "正在保存…" : accepted ? "复核并保存新映射版本" : "保存明确分支映射"}</Button>
    </>}
  </article>;
}
