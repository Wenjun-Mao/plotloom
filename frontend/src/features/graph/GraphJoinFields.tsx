import { Field } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";

export function GraphJoinFields({ joinId, disabled }: { joinId: string; disabled: boolean }) {
  const owner = useGraphWorkbench(), draft = owner.draft!;
  const join = draft.mapping.topology.joins.find(join => join.id === joinId)!;
  const update = (field: "requiredStateKeys" | "allowedDifferences", value: string, commit: boolean) => {
    const next = structuredClone(owner.draft!), key = `join:${join.id}:${field}`;
    next.fieldBuffers[key] = value;
    if (commit) {
      next.mapping.topology.joins.find(item => item.id === join.id)![field] = value.split("\n").map(value => value.trim()).filter(Boolean);
      delete next.fieldBuffers[key];
    }
    owner.changeDraft(next);
  };
  return <>{(["requiredStateKeys", "allowedDifferences"] as const).map(field => <Field key={field}
    label={field === "requiredStateKeys" ? "必须一致的状态键（每行一个）" : "允许差异（每行一个）"}>
    <textarea rows={3} disabled={disabled} value={draft.fieldBuffers[`join:${join.id}:${field}`] ?? join[field].join("\n")}
      onChange={event => update(field, event.target.value, false)} onBlur={event => update(field, event.target.value, true)} />
  </Field>)}</>;
}
