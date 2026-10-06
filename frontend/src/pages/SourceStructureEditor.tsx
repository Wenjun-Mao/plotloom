import type { GraphMapDraft } from "../features/graph/contracts";
import { RequiredMark } from "../components";

export function SourceStructureEditor({ mapping, disabled, onChange }: { mapping: GraphMapDraft; disabled: boolean; onChange: (mapping: GraphMapDraft) => void }) {
  const title = (id: string | null) => id === null ? "待连接" : mapping.sections.find(section => section.sectionId === id)?.title || "待填写剧情节点";
  const choices = mapping.choices;
  const changeChoice = (index: number, change: Partial<(typeof choices)[number]>) => {
    const next = choices.map((choice, i) => i === index ? { ...choice, ...change } : choice);
    onChange({ ...mapping, choices: next });
  };
  return <>
    <div className="section-map-sections">{mapping.sections.map((section, index) => {
      const kind = mapping.topology?.nodes.find(node => node.id === section.sectionId)?.kind;
      const label = kind === "decision" ? "选择节点" : kind === "join" ? "分支汇合" : section.ending ? "结局" : index === 0 ? "共同开场" : "后续剧情";
      return <fieldset key={section.sectionId}><legend>{label} · 第 {index + 1} 个剧情节点</legend>
        <label><span>章节标题<RequiredMark /></span><input aria-required="true" disabled={disabled} value={section.title} onChange={event => onChange({ ...mapping, sections: mapping.sections.map((item, i) => i === index ? { ...item, title: event.target.value } : item) })} /></label>
        <label><span>章节摘要<RequiredMark /></span><textarea rows={3} aria-required="true" disabled={disabled} value={section.summary} onChange={event => onChange({ ...mapping, sections: mapping.sections.map((item, i) => i === index ? { ...item, summary: event.target.value } : item) })} /></label>
        {(kind === "decision" || kind === "join") && <label><input type="checkbox" disabled={disabled} checked={section.footageMode === "footage"} onChange={event => onChange({ ...mapping, topologyOrigin: "author", sections: mapping.sections.map((item, i) => i === index ? { ...item, footageMode: event.target.checked ? "footage" : "route_only" } : item) })} />为此路线控制节点包含画面</label>}
        <details><summary>技术详情：章节标识</summary><code>{section.sectionId}</code></details>
      </fieldset>;
    })}</div>
    {choices.map((choice, choiceIndex) => <fieldset className="section-map-choice" key={choice.choiceId}><legend>播放时的剧情选择 · {title(choice.sectionId)}</legend>
      <label><span>播放时显示的问题<RequiredMark /></span><textarea rows={2} aria-required="true" disabled={disabled} value={choice.prompt} onChange={event => changeChoice(choiceIndex, { prompt: event.target.value })} /></label>
      {choice.outcomes.map((option, index) => <div className="section-map-outcome" key={option.outcomeId}><strong>选项 {String.fromCharCode(65 + index)}</strong>
        <label><span>选项文字<RequiredMark /></span><input aria-required="true" disabled={disabled} value={option.label} onChange={event => changeChoice(choiceIndex, { outcomes: choice.outcomes.map((item, i) => i === index ? { ...item, label: event.target.value } : item) })} /></label>
        <label><span>选择后的剧情<RequiredMark /></span><textarea rows={2} aria-required="true" disabled={disabled} value={option.consequence} onChange={event => changeChoice(choiceIndex, { outcomes: choice.outcomes.map((item, i) => i === index ? { ...item, consequence: event.target.value } : item) })} /></label>
        <p>{mapping.sections.find(section => section.sectionId === option.endingSectionId)?.ending ? "对应结局" : "进入后续剧情"}：{title(option.endingSectionId)}</p>
        <details><summary>技术详情：选项与链接</summary><code>{option.outcomeId} → {option.endingSectionId}</code></details>
      </div>)}
    </fieldset>)}
    {mapping.topology?.joins.map(join => <label className="field" key={join.id}><span>汇合后的叙事衔接：{title(join.joinNodeId)}<RequiredMark /></span><textarea aria-required="true" rows={3} disabled={disabled} value={mapping.joinReconciliations?.[join.id] || ""} onChange={event => onChange({ ...mapping, joinReconciliations: { ...mapping.joinReconciliations, [join.id]: event.target.value } })} /></label>)}
  </>;
}
