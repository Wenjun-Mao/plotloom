import { Button, Field } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import type { DraftEdge } from "./contracts";
import { storyNodeKindLabels } from "./presentation";

export function GraphEdgeDetails({ edge, disabled }: { edge: DraftEdge; disabled: boolean }) {
  const owner = useGraphWorkbench(), draft = owner.draft!;
  const nodes = draft.mapping.topology.nodes;
  const choice = draft.mapping.choices.find(choice => choice.outcomes.some(option => option.outcomeId === edge.id));
  const option = choice?.outcomes.find(option => option.outcomeId === edge.id);
  const title = (identity: string) => draft.mapping.sections.find(section => section.sectionId === identity)?.title || identity;
  const updateJson = (field: "stateEffects" | "entityStateEffects", value: string, commit: boolean) => {
    const key = `edge:${edge.id}:${field}`, next = structuredClone(owner.draft!);
    next.fieldBuffers[key] = value;
    try {
      const parsed = JSON.parse(value);
      if (field === "stateEffects" ? parsed === null || Array.isArray(parsed) || typeof parsed !== "object" : !Array.isArray(parsed)) throw new Error("wrong field shape");
      if (field === "entityStateEffects" && parsed.some((item: Record<string, unknown>) => !item || !["character", "location", "prop"].includes(String(item.entityType))
        || typeof item.entityId !== "string" || !/^[a-z][a-z0-9_-]{1,63}$/.test(item.entityId) || typeof item.state !== "string" || !item.state.trim())) throw new Error("incomplete entity state");
      const target = next.mapping.topology.edges.find(item => item.id === edge.id)!;
      if (field === "stateEffects") target.stateEffects = parsed;
      else target.entityStateEffects = parsed;
      if (commit) delete next.fieldBuffers[key];
    } catch { /* The typed field buffer retains unfinished input for recovery. */ }
    owner.changeDraft(next);
  };
  return <section className="graph-edge-detail" data-edge-id={edge.id}>
    <strong>{edge.kind === "choice" ? "选项" : "连接"} · {edge.id}</strong>
    {option && <><Field label="保留的选项文字"><input disabled={disabled} value={option.label} onChange={event => owner.changeMapping({ ...draft.mapping,
      choices: draft.mapping.choices.map(item => item.choiceId === choice!.choiceId ? { ...item, outcomes: item.outcomes.map(value => value.outcomeId === edge.id ? { ...value, label: event.target.value } : value) } : item) })} /></Field>
      <Field label="保留的后续剧情"><textarea rows={2} disabled={disabled} value={option.consequence} onChange={event => owner.changeMapping({ ...draft.mapping,
        choices: draft.mapping.choices.map(item => item.choiceId === choice!.choiceId ? { ...item, outcomes: item.outcomes.map(value => value.outcomeId === edge.id ? { ...value, consequence: event.target.value } : value) } : item) })} /></Field></>}
    {(["source", "target"] as const).map(endpoint => <Field key={endpoint} label={endpoint === "source" ? "输入来自" : "输出通往"}>
      <select aria-label={`${edge.id} ${endpoint === "source" ? "起点" : "终点"}`} disabled={disabled} value={(endpoint === "source" ? edge.sourceNodeId : edge.targetNodeId) ?? ""}
        onChange={event => void owner.prepareCommand({ operation: "retarget", edgeId: edge.id, endpoint, nodeId: event.target.value || null })}>
        <option value="">待连接</option>{nodes.map(node => <option key={node.id} value={node.id}>{title(node.id)} · {storyNodeKindLabels[node.kind]}</option>)}
      </select>
      {owner.draft?.detachedEndpoints[edge.id]?.[endpoint] && <small>保留原{endpoint === "source" ? "起点" : "目标"}：{owner.draft.detachedEndpoints[edge.id][endpoint]!.title || owner.draft.detachedEndpoints[edge.id][endpoint]!.nodeId}</small>}
    </Field>)}
    <details><summary>状态与实体效果</summary>
      <p>事实使用 JSON 对象，实体状态使用当前故事圣经引用数组。未完成输入可保存草稿，提交字段后才能确认内容。</p>
      {(["stateEffects", "entityStateEffects"] as const).map(field => {
        const key = `edge:${edge.id}:${field}`, value = draft.fieldBuffers[key] ?? JSON.stringify(edge[field], null, 2);
        return <Field key={field} label={field === "stateEffects" ? "事实效果 JSON" : "实体状态 JSON"}><textarea rows={5} disabled={disabled} value={value}
          onChange={event => updateJson(field, event.target.value, false)} onBlur={event => updateJson(field, event.target.value, true)} />
          {key in draft.fieldBuffers && <small>字段输入待提交；原有效效果与当前输入均保留。</small>}</Field>;
      })}
    </details>
    <Button variant="danger" disabled={disabled} onClick={() => void owner.prepareCommand({ operation: "remove_edge", edgeId: edge.id })}>删除这条连接</Button>
  </section>;
}
