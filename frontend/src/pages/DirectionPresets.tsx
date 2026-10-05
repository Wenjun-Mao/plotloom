import { useState } from "react";
import type { DirectionSelection } from "../types";
import { Button, Field } from "../components";

type Group = { id: DirectionSelection["group"]; label: string; values: string[] };
export const genreGroups: Group[] = [
  { id: "subject", label: "题材背景", values: ["都市", "科幻", "奇幻", "历史"] },
  { id: "narrative", label: "叙事类型", values: ["剧情", "悬疑", "爱情", "喜剧", "冒险", "惊悚"] },
];
export const visualGroups: Group[] = [
  { id: "representation", label: "表现形式", values: ["真人写实", "2D 动画", "3D 动画"] },
  { id: "treatment", label: "美术风格", values: ["水墨", "水彩", "复古", "赛博朋克"] },
  { id: "lighting", label: "色彩与光线", values: ["暖色", "冷色", "低饱和", "高反差"] },
];

function PresetGroup({ group, value, disabled, onChange }: { group: Group; value: DirectionSelection[]; disabled: boolean; onChange: (value: DirectionSelection[]) => void }) {
  const [custom, setCustom] = useState("");
  const has = (text: string) => value.some(item => item.group === group.id && item.value === text);
  const toggle = (text: string) => onChange(has(text) ? value.filter(item => item.group !== group.id || item.value !== text) : [...value, { group: group.id, value: text }]);
  return <fieldset><legend>{group.label}</legend><div className="preset-options">
    {group.values.map(text => <button type="button" className="button quiet" aria-pressed={has(text)} disabled={disabled} key={text} onClick={() => toggle(text)}>{text}</button>)}
  </div><details className="preset-custom-disclosure"><summary>添加{group.label}自定义</summary><div className="preset-custom"><input aria-label={`${group.label}自定义`} maxLength={120} value={custom} disabled={disabled} placeholder="自定义内容" onChange={event => setCustom(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); if (custom.trim() && !has(custom.trim())) { toggle(custom.trim()); setCustom(""); } } }} /><Button variant="quiet" disabled={disabled || !custom.trim() || has(custom.trim())} onClick={() => { toggle(custom.trim()); setCustom(""); }}>＋自定义</Button></div></details></fieldset>;
}

export function DirectionPresets({ label, groups, selections, detail, disabled, onSelections, onDetail }: { label: string; groups: Group[]; selections: DirectionSelection[]; detail: string; disabled: boolean; onSelections: (value: DirectionSelection[]) => void; onDetail: (value: string) => void }) {
  return <section className="direction-presets" aria-label={label}><h2>{label} <small>可选，可组合</small></h2>
    <div className="preset-selections" aria-label={`已选${label}`}>{selections.length ? selections.map(item => <Button key={`${item.group}:${item.value}`} variant="quiet" disabled={disabled} aria-label={`移除${item.value}`} onClick={() => onSelections(selections.filter(next => next !== item))}>{item.value} ×</Button>) : <span className="muted">尚未选择</span>}</div>
    {groups.map(group => <PresetGroup key={group.id} group={group} value={selections} disabled={disabled || selections.length >= 40} onChange={onSelections} />)}
    {label === "视觉风格" && <p className="action-prerequisite">建议明确主要表现形式；也可以有意混搭，请在细节中说明如何结合。</p>}
    <Field label={`${label}细节（可选）`}><textarea rows={2} disabled={disabled} value={detail} onChange={event => onDetail(event.target.value)} /><small>原有自由文本保留在这里，与已选内容一起用于创作。</small></Field>
  </section>;
}
