import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Button, ErrorNotice } from "../components";
import { useAutomaticGuidance, useKnownAutomaticRun } from "../features/autopilot/guidance";
import { useAdoptionLabel } from "../features/autopilot/AutopilotWorkspace";
import type { PresentationSpan, ProductionBridgeProposal, PresentationSource, PresentationCandidate } from "../types";

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

/** Every source remains readable; specialist advice is never author approval. */
export function ProductionPresentationReview({ projectId, proposal, candidate, disabled, accepted, onSave, onDirty, onEdited }: {
  projectId: string; proposal: ProductionBridgeProposal; candidate?: PresentationCandidate | null; disabled: boolean; accepted: boolean;
  onSave: (entries: Array<{ id: string; spans: PresentationSpan[] }>) => Promise<boolean>;
  onDirty: (dirty: boolean) => void; onEdited?: () => void;
}) {
  const automatic = useAutomaticGuidance();
  const knownAutomatic = useKnownAutomaticRun();
  const adoption = useAdoptionLabel()("bridge-presentation", proposal.revision, proposal.contentHash);
  const pkg = proposal.presentation;
  const currentCandidate = candidate?.proposalRevision === proposal.revision
    && candidate.proposalContentHash === proposal.contentHash && candidate.sourceHash === pkg.sourceHash ? candidate : undefined;
  const [entries, setEntries] = useState<Record<string, PresentationSpan[]>>({});
  const [appliedJob, setAppliedJob] = useState<string>();
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [selection, setSelection] = useState<{ id: string; start: number; end: number }>();
  const ownership = useRef(0), edited = useRef(false);
  useLayoutEffect(() => { ownership.current += 1; edited.current = false; return () => { ownership.current += 1; }; }, [projectId, pkg.sourceHash]);
  const baseline = JSON.stringify(pkg.sources.map(source => ({ id: source.id, spans: source.spans })));
  const apply = () => {
    setEntries(currentCandidate ? Object.fromEntries(currentCandidate.entries.map(entry => [entry.id, entry.spans]))
      : Object.fromEntries(pkg.sources.map(source => [source.id, initial(source)])));
    setAppliedJob(currentCandidate?.jobId); setSelection(undefined); setError("");
  };
  const restoreOrPrefill = () => {
    if (pkg.reviewed) {
      setEntries(Object.fromEntries(pkg.sources.map(source => [source.id, initial(source)]))); setAppliedJob(undefined);
    } else apply();
  };
  useEffect(() => { edited.current = false; restoreOrPrefill(); setBusy(false); onDirty(false); }, [projectId, pkg.sourceHash]);
  useEffect(() => { if (!edited.current) restoreOrPrefill(); }, [baseline, currentCandidate?.jobId]);
  const dirty = JSON.stringify(pkg.sources.map(source => ({ id: source.id, spans: entries[source.id] ?? [] }))) !== baseline;
  useEffect(() => { onDirty(dirty); }, [dirty]);
  const change = (id: string, index: number, update: Partial<PresentationSpan>) => {
    edited.current = true; onEdited?.();
    setEntries(current => ({ ...current, [id]: current[id].map((span, position) => position === index ? { ...span, ...update } : span) }));
  };
  const split = (source: PresentationSource) => {
    if (!selection || selection.id !== source.id || selection.end <= selection.start) return;
    edited.current = true; onEdited?.();
    setEntries(current => ({ ...current, [source.id]: splitPresentationSpans(current[source.id], selection.start, selection.end) })); setSelection(undefined);
  };
  const sourceComplete = (source: PresentationSource) => !!entries[source.id]?.length && entries[source.id].every(span =>
    span.role !== "unassigned" && (span.role !== "physical" || span.rendering.trim())
    && (!["runtime_choice", "review_only"].includes(span.role) || span.reason.trim()));
  const unresolved = pkg.sources.filter(source => !sourceComplete(source)).length;
  const groups = new Map<string, { title: string; sources: PresentationSource[] }>();
  pkg.sources.forEach(source => {
    const { episode, sceneIndex } = source.coordinates, key = JSON.stringify([episode, sceneIndex]);
    if (!groups.has(key)) groups.set(key, { title: episode && sceneIndex ? `第 ${episode} 结构条目 · 场次 ${sceneIndex}` : "来源条目", sources: [] });
    groups.get(key)!.sources.push(source);
  });
  return <details open className="presentation-review" data-testid="production-presentation-review"><summary>逐项审阅内容的呈现方式</summary>
    <p>{knownAutomatic ? `${adoption}的呈现方案仍待整包人工审阅；手动保存修改将接管自动运行。` : automatic || "按场次查看，修改呈现方式后确认保存。原始剧本与分镜保持不变。"}</p>
    <details><summary>呈现方式说明</summary><p>实体动作与限制须完整保留；画面文字保留原文且不发声。选择问题与按钮由播放器呈现。混合描述可展开原文并拆分；实际媒体仍需单独审核。</p></details>
    {currentCandidate && <div className="notice" role="status">{appliedJob === currentCandidate.jobId ? "助手建议 · 已填入下方，可逐项修改；尚未确认保存。" : "助手建议已返回；你的本地编辑保留，未被覆盖。"}
      {appliedJob !== currentCandidate.jobId && <Button disabled={disabled || busy} onClick={() => { edited.current = true; onEdited?.(); apply(); }}>使用助手建议替换本地呈现编辑</Button>}
    </div>}
    <details><summary>播放器选择 · {pkg.runtimeChoice.choices.length} 项</summary>{pkg.runtimeChoice.choices.map(choice =>
      <p key={choice.choiceId}>{choice.prompt} · {choice.outcomes.map(outcome => outcome.label).join(" / ")}</p>)}</details>
    {[...groups].map(([key, group], groupIndex) => <details key={key} className="presentation-scene" open={groupIndex === 0}>
      <summary>{group.title}<small>{group.sources.length} 项 · {group.sources.filter(source => !sourceComplete(source)).length ? `${group.sources.filter(source => !sourceComplete(source)).length} 项待完善` : "呈现方式已填齐"}</small></summary>
      {group.sources.map((source, sourceIndex) => <fieldset key={source.id} className="presentation-source" data-source-id={source.id} disabled={disabled || busy || accepted}>
        <legend>{source.kind === "composition" ? `镜头 ${group.sources.slice(0, sourceIndex + 1).filter(item => item.kind === "composition").length} · 构图` : `${source.kind === "dialogue" ? "对白" : "动作"} ${source.coordinates.flowIndex ?? sourceIndex + 1}`}
          {appliedJob && currentCandidate && <small>助手建议{edited.current ? " · 可修改" : ""}</small>}</legend>
        <details className="presentation-raw"><summary>查看原文并拆分</summary>
          <textarea aria-label={`原始来源 ${source.id}`} readOnly value={source.sourceText} onSelect={event => {
            const element = event.currentTarget;
            setSelection({ id: source.id, start: [...element.value.slice(0, element.selectionStart)].length, end: [...element.value.slice(0, element.selectionEnd)].length });
          }} />
          <Button disabled={!selection || selection.id !== source.id || selection.start === selection.end} onClick={() => split(source)}>拆分选中文本</Button>
        </details>
        {(entries[source.id] ?? []).map((span, index) => <div className="presentation-span" key={`${span.start}:${span.end}`}>
          <blockquote>{slice(source.sourceText, span.start, span.end)}</blockquote>
          <label>这段内容由谁呈现<select aria-label={`归属 ${source.id} ${index + 1}`} value={span.role} onChange={event => change(source.id, index, { role: event.target.value as PresentationSpan["role"], rendering: "", reason: "" })}>
            {Object.entries(roles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
          {span.role === "physical" && <label>忠实画面描述<textarea aria-label={`画面描述 ${source.id} ${index + 1}`} value={span.rendering} onChange={event => change(source.id, index, { rendering: event.target.value })} /></label>}
          {["runtime_choice", "review_only"].includes(span.role) && <label>归属说明<textarea aria-label={`归属说明 ${source.id} ${index + 1}`} value={span.reason} onChange={event => change(source.id, index, { reason: event.target.value })} /></label>}
        </div>)}
        <details><summary>来源坐标与摘要</summary><pre>{JSON.stringify({ id: source.id, targetId: source.targetId, coordinates: source.coordinates, sourceHash: source.sourceHash }, null, 2)}</pre></details>
      </fieldset>)}
    </details>)}
    <details><summary>完整原始 F4 / F5 / 选择来源（只读）</summary><pre>{JSON.stringify(pkg.frozenEvidence, null, 2)}</pre></details>
    {!accepted && <div className="presentation-save" role="group" aria-label="呈现方式 · 确认保存">
      <div className="bridge-intent-save-copy"><div><strong>呈现方式 · 共 {pkg.sources.length} 项</strong><span role="status">{unresolved ? `还有 ${unresolved} 项待完善` : pkg.reviewed && !dirty ? "呈现方式已保存" : "呈现方式已填齐，待确认保存"}</span></div>
        <p>保存表示采用当前呈现方式；不会确认投产或生成图片、视频。</p></div>
      <Button variant="primary" disabled={disabled || busy || unresolved > 0} onClick={() => {
        const epoch = ownership.current; setBusy(true); setError("");
        void onSave(pkg.sources.map(source => ({ id: source.id, spans: entries[source.id] })))
          .then(saved => { if (saved && ownership.current === epoch) onDirty(false); })
          .catch(reason => { if (ownership.current === epoch) setError(reason instanceof Error ? reason.message : "无法保存呈现审阅"); })
          .finally(() => { if (ownership.current === epoch) setBusy(false); });
      }}>确认并保存呈现方式</Button>
    </div>}
    {pkg.reviewed && <p>{accepted ? "呈现方式审阅已保存；实际媒体仍需单独审核并选用。" : "呈现方式审阅已保存；修改后请重新保存。实际媒体仍需单独审核并选用。"}</p>}
    {error && <ErrorNotice message={error} />}
  </details>;
}
