import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Button, ErrorNotice } from "../components";
import type { PresentationSpan, ProductionBridgeProposal, PresentationSource } from "../types";

const initial = (source: PresentationSource): PresentationSpan[] => source.spans.length ? source.spans : [{ start: 0, end: [...source.sourceText].length, role: "unassigned", rendering: "", reason: "" }];
const roles = { unassigned: "请选择归属", physical: "实体动作 / 构图", visible_text: "画面内准确文字（不发声）", runtime_choice: "播放器选择界面", review_only: "仅评审说明（注明理由）", dialogue: "台词（由对白条目负责）" } as const;
const slice = (text: string, start: number, end: number) => [...text].slice(start, end).join("");

export function splitPresentationSpans(spans: PresentationSpan[], start: number, end: number): PresentationSpan[] {
  return spans.flatMap(span => {
    const cuts = [start, end].filter(point => point > span.start && point < span.end);
    if (!cuts.length) return [span];
    const boundaries = [...new Set([span.start, ...cuts, span.end])].sort((a, b) => a - b);
    return boundaries.slice(0, -1).map((point, index) => ({ start: point, end: boundaries[index + 1], role: "unassigned" as const, rendering: "", reason: "" }));
  });
}

/** Every source fragment stays visible; semantic ownership is an explicit review. */
export function ProductionPresentationReview({ projectId, proposal, disabled, accepted, onSave, onDirty, onEdited }: {
  projectId: string; proposal: ProductionBridgeProposal; disabled: boolean; accepted: boolean;
  onSave: (entries: Array<{ id: string; spans: PresentationSpan[] }>) => Promise<boolean>;
  onDirty: (dirty: boolean) => void;
  onEdited?: () => void;
}) {
  const pkg = proposal.presentation;
  const [entries, setEntries] = useState<Record<string, PresentationSpan[]>>({});
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selection, setSelection] = useState<{ id: string; start: number; end: number }>();
  const ownership = useRef(0);
  useLayoutEffect(() => { ownership.current += 1; return () => { ownership.current += 1; }; }, [projectId, pkg.sourceHash]);
  const baseline = JSON.stringify(pkg.sources.map(source => ({ id: source.id, spans: source.spans })));
  useEffect(() => {
    setEntries(Object.fromEntries(pkg.sources.map(source => [source.id, initial(source)])));
    setConfirmed(false); setError(""); setBusy(false); setSelection(undefined); onDirty(false);
  }, [projectId, pkg.sourceHash]);
  const dirty = JSON.stringify(pkg.sources.map(source => ({ id: source.id, spans: entries[source.id] ?? [] }))) !== baseline;
  useEffect(() => { onDirty(dirty); }, [dirty]);
  const change = (id: string, index: number, update: Partial<PresentationSpan>) => {
    onEdited?.();
    setEntries(current => ({ ...current, [id]: current[id].map((span, position) => position === index ? { ...span, ...update } : span) }));
    setConfirmed(false);
  };
  const split = (source: PresentationSource) => {
    if (!selection || selection.id !== source.id || selection.end <= selection.start) return;
    onEdited?.();
    setEntries(current => ({ ...current, [source.id]: splitPresentationSpans(current[source.id], selection.start, selection.end) })); setConfirmed(false); setSelection(undefined);
  };
  const complete = pkg.sources.every(source => entries[source.id]?.every(span => span.role !== "unassigned" && (span.role !== "physical" || span.rendering.trim()) && (!["runtime_choice", "review_only"].includes(span.role) || span.reason.trim())));
  return <details open data-testid="production-presentation-review"><summary>逐项审阅内容的呈现方式</summary>
    <p>原始剧本与分镜保持不变。逐项核对所有动作、限制与文字；混合描述可选中文本后拆分；只有被拆开的片段需要重新填写归属，其他编辑保持不变。播放器负责提问和按钮；画面内文字须保留原文且不发声。预留区域不代表已有文字合成器，实际媒体仍须检查。</p>
    {pkg.runtimeChoice.choices.map(choice => <p key={choice.choiceId}>播放器选择：{choice.prompt} · {choice.outcomes.map(outcome => outcome.label).join(" / ")}</p>)}
    {pkg.sources.map(source => <fieldset key={source.id} disabled={disabled || busy || accepted}>
      <legend>{source.kind === "composition" ? "构图" : source.kind === "dialogue" ? "对白" : "动作"} · {source.targetId}</legend>
      <textarea aria-label={`原始来源 ${source.id}`} readOnly value={source.sourceText} onSelect={event => {
        const element = event.currentTarget;
        setSelection({ id: source.id, start: [...element.value.slice(0, element.selectionStart)].length, end: [...element.value.slice(0, element.selectionEnd)].length });
      }} />
      <Button disabled={!selection || selection.id !== source.id || selection.start === selection.end} onClick={() => split(source)}>拆分选中文本</Button>
      {(entries[source.id] ?? []).map((span, index) => <div key={`${span.start}:${span.end}`}>
        <blockquote>{slice(source.sourceText, span.start, span.end)}</blockquote>
        <label>这段内容由谁呈现<select aria-label={`归属 ${source.id} ${index + 1}`} value={span.role} onChange={event => change(source.id, index, { role: event.target.value as PresentationSpan["role"], rendering: "", reason: "" })}>
          {Object.entries(roles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        {span.role === "physical" && <label>忠实画面描述（保留全部实体动作与限制）<textarea aria-label={`画面描述 ${source.id} ${index + 1}`} value={span.rendering} onChange={event => change(source.id, index, { rendering: event.target.value })} /></label>}
        {["runtime_choice", "review_only"].includes(span.role) && <label>归属说明<textarea aria-label={`归属说明 ${source.id} ${index + 1}`} value={span.reason} onChange={event => change(source.id, index, { reason: event.target.value })} /></label>}
      </div>)}
      <details><summary>来源坐标与摘要</summary><pre>{JSON.stringify({ coordinates: source.coordinates, sourceHash: source.sourceHash }, null, 2)}</pre></details>
    </fieldset>)}
    <details><summary>完整原始 F4 / F5 / 选择来源（只读）</summary><pre>{JSON.stringify(pkg.frozenEvidence, null, 2)}</pre></details>
    {!accepted && <><label><input type="checkbox" checked={confirmed} disabled={disabled || busy || !complete} onChange={event => setConfirmed(event.target.checked)} />我已逐项核对全部来源：动作与限制完整，画面文字准确且不发声，选择问题与选项由播放器负责。</label>
      <Button disabled={disabled || busy || !complete || !confirmed} onClick={() => {
        const epoch = ownership.current;
        setBusy(true); setError("");
        void onSave(pkg.sources.map(source => ({ id: source.id, spans: entries[source.id] })))
          .then(saved => { if (saved && ownership.current === epoch) { onDirty(false); setConfirmed(false); } })
          .catch(reason => { if (ownership.current === epoch) setError(reason instanceof Error ? reason.message : "无法保存呈现审阅"); })
          .finally(() => { if (ownership.current === epoch) setBusy(false); });
      }}>保存呈现方式审阅</Button></>}
    {pkg.reviewed && <p>{accepted ? "呈现方式审阅已保存；实际媒体仍需单独审核并选用。" : "呈现方式审阅已保存；修改后请重新保存。实际媒体仍需单独审核并选用。"}</p>}
    {error && <ErrorNotice message={error} />}
  </details>;
}
