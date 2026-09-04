import { useEffect, useState } from "react";
import type { ContinuityState, EntityType, RequiredEntityState } from "./types";
import { Button, Field } from "./components";

export type StructuredValueKind = "string" | "number" | "boolean" | "null" | "json";

export interface EntityOption {
  type: EntityType;
  id: string;
  label: string;
  states: string[];
}

export function structuredValueKind(value: unknown): StructuredValueKind {
  if (value === null) return "null";
  if (typeof value === "string") return "string";
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  return "json";
}

export function valueForKind(kind: StructuredValueKind): unknown {
  if (kind === "string") return "";
  if (kind === "number") return 0;
  if (kind === "boolean") return false;
  if (kind === "null") return null;
  return {};
}

function nextRecordKey(value: Record<string, unknown>): string {
  let index = Object.keys(value).length + 1;
  while (`field_${index}` in value) index += 1;
  return `field_${index}`;
}

function renameRecordKey(
  value: Record<string, unknown>,
  oldKey: string,
  nextKey: string,
): Record<string, unknown> {
  if (nextKey === oldKey) return value;
  const renamed: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    renamed[key === oldKey ? nextKey : key] = item;
  }
  return renamed;
}

function StructuredValueInput({
  value,
  onChange,
  focusKey,
  focusField,
}: {
  value: unknown;
  onChange: (value: unknown) => void;
  focusKey?: string;
  focusField?: string;
}) {
  const kind = structuredValueKind(value);
  const [jsonText, setJsonText] = useState(kind === "json" ? JSON.stringify(value, null, 2) : "");
  const [jsonError, setJsonError] = useState("");
  useEffect(() => {
    if (kind === "json") setJsonText(JSON.stringify(value, null, 2));
  }, [kind, value]);

  if (kind === "boolean") {
    return <select data-focus-key={focusKey} data-focus-field={focusField} value={String(value)} onChange={(event) => onChange(event.target.value === "true")}><option value="true">true</option><option value="false">false</option></select>;
  }
  if (kind === "null") return <input data-focus-key={focusKey} data-focus-field={focusField} value="null" readOnly />;
  if (kind === "json") {
    return <div className="structured-json-value"><textarea data-focus-key={focusKey} data-focus-field={focusField} rows={3} value={jsonText} aria-invalid={Boolean(jsonError)} onChange={(event) => {
      const next = event.target.value;
      setJsonText(next);
      try { onChange(JSON.parse(next)); setJsonError(""); }
      catch { setJsonError("请输入有效 JSON 对象或数组"); }
    }} />{jsonError && <small role="alert">{jsonError}</small>}</div>;
  }
  return <input data-focus-key={focusKey} data-focus-field={focusField} type={kind === "number" ? "number" : "text"} value={String(value)} onChange={(event) => onChange(kind === "number" ? Number(event.target.value) : event.target.value)} />;
}

function RecordRow({ name, value, allNames, onRename, onValue, onRemove, focusKey, focusField }: {
  name: string;
  value: unknown;
  allNames: string[];
  onRename: (name: string) => void;
  onValue: (value: unknown) => void;
  onRemove: () => void;
  focusKey?: string;
  focusField?: string;
}) {
  const [nameDraft, setNameDraft] = useState(name);
  const [nameError, setNameError] = useState("");
  useEffect(() => setNameDraft(name), [name]);
  const commitName = () => {
    const normalized = nameDraft.trim();
    if (!normalized) { setNameError("键不能为空"); return; }
    if (normalized !== name && allNames.includes(normalized)) { setNameError("键不能重复"); return; }
    setNameError(""); onRename(normalized); setNameDraft(normalized);
  };
  const rowFocusKey = focusKey ? `${focusKey}.${name}` : undefined;
  const rowFocusField = focusField ? `${focusField}.${name}` : undefined;
  return <div className="structured-row" data-record-key={name} data-focus-key={rowFocusKey} data-focus-field={rowFocusField} tabIndex={rowFocusKey ? -1 : undefined}>
    <div><input data-focus-key={rowFocusKey ? `${rowFocusKey}.key` : undefined} data-focus-field={rowFocusField ? `${rowFocusField}.key` : undefined} aria-label="键" value={nameDraft} aria-invalid={Boolean(nameError)} onChange={(event) => setNameDraft(event.target.value)} onBlur={commitName} />{nameError && <small role="alert">{nameError}</small>}</div>
    <select data-focus-key={rowFocusKey ? `${rowFocusKey}.type` : undefined} data-focus-field={rowFocusField ? `${rowFocusField}.type` : undefined} aria-label="值类型" value={structuredValueKind(value)} onChange={(event) => onValue(valueForKind(event.target.value as StructuredValueKind))}><option value="string">文字</option><option value="number">数字</option><option value="boolean">布尔</option><option value="null">null</option><option value="json">JSON</option></select>
    <StructuredValueInput value={value} onChange={onValue} focusKey={rowFocusKey ? `${rowFocusKey}.value` : undefined} focusField={rowFocusField ? `${rowFocusField}.value` : undefined} />
    <Button variant="quiet" aria-label={`删除键 ${name}`} onClick={onRemove}>删除</Button>
  </div>;
}

export function TypedRecordEditor({ label, value, onChange, testId, focusKey, focusField }: {
  label: string;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
  testId?: string;
  /** Stable owner key; each record row appends its current author-defined key. */
  focusKey?: string;
  /** Relative canonical path used by parent entity-scope routing. */
  focusField?: string;
}) {
  const names = Object.keys(value);
  return <fieldset className="structured-editor" data-testid={testId} data-focus-key={focusKey} data-focus-field={focusField} tabIndex={focusKey ? -1 : undefined}><legend>{label}</legend>
    {!names.length && <small>尚无结构化条目。</small>}
    {names.map((name) => <RecordRow key={name} name={name} value={value[name]} allNames={names} focusKey={focusKey} focusField={focusField} onRename={(nextName) => onChange(renameRecordKey(value, name, nextName))} onValue={(nextValue) => onChange({ ...value, [name]: nextValue })} onRemove={() => onChange(Object.fromEntries(Object.entries(value).filter(([key]) => key !== name)))} />)}
    <Button variant="quiet" onClick={() => { const key = nextRecordKey(value); onChange({ ...value, [key]: "" }); }}>＋ 添加键值</Button>
  </fieldset>;
}

export function StringListEditor({ label, value, onChange, rows = 3 }: {
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
  rows?: number;
}) {
  return <Field label={label}><textarea rows={rows} value={value.join("\n")} onChange={(event) => onChange(event.target.value.split("\n").map((item) => item.trim()).filter(Boolean))} /></Field>;
}

export function EntityStateEditor({ label, value, options, onChange, focusKey }: {
  label: string;
  value: RequiredEntityState[];
  options: EntityOption[];
  onChange: (value: RequiredEntityState[]) => void;
  focusKey?: string;
}) {
  const add = () => {
    const available = options.find((option) => !value.some((state) => state.entityType === option.type && state.entityId === option.id));
    if (!available) return;
    onChange([...value, { entityType: available.type, entityId: available.id, state: available.states[0] ?? "" }]);
  };
  return <fieldset className="structured-editor" data-focus-key={focusKey} tabIndex={focusKey ? -1 : undefined}><legend>{label}</legend>
    {!value.length && <small>尚未声明实体状态。</small>}
    {value.map((state, index) => {
      const matching = options.find((option) => option.type === state.entityType && option.id === state.entityId);
      return <div className="structured-row entity-state-row" key={`${state.entityType}:${state.entityId}`}>
        <select data-focus-key={focusKey ? `${focusKey}.${index}.entityId` : undefined} aria-label="实体" value={`${state.entityType}:${state.entityId}`} onChange={(event) => {
          const next = options.find((option) => `${option.type}:${option.id}` === event.target.value);
          if (!next) return;
          onChange(value.map((item, itemIndex) => itemIndex === index ? { entityType: next.type, entityId: next.id, state: next.states[0] ?? "" } : item));
        }}>{options.map((option) => <option key={`${option.type}:${option.id}`} value={`${option.type}:${option.id}`}>{option.label}</option>)}</select>
        <select data-focus-key={focusKey ? `${focusKey}.${index}.state` : undefined} aria-label="状态" value={state.state} onChange={(event) => onChange(value.map((item, itemIndex) => itemIndex === index ? { ...item, state: event.target.value } : item))}>{matching?.states.map((stateName) => <option key={stateName} value={stateName}>{stateName}</option>)}{!matching?.states.includes(state.state) && <option value={state.state}>{state.state || "未设置"}</option>}</select>
        <Button variant="quiet" onClick={() => onChange(value.filter((_, itemIndex) => itemIndex !== index))}>删除</Button>
      </div>;
    })}
    <Button variant="quiet" disabled={!options.length || value.length >= options.length} onClick={add}>＋ 添加实体状态</Button>
  </fieldset>;
}

export function ContinuityStateEditor({ label, value, options, onChange, focusKey }: {
  label: string;
  value: ContinuityState;
  options: EntityOption[];
  onChange: (value: ContinuityState) => void;
  focusKey?: string;
}) {
  return <details className="continuity-editor" data-focus-key={focusKey} tabIndex={focusKey ? -1 : undefined}><summary>{label}</summary>
    <TypedRecordEditor focusKey={focusKey ? `${focusKey}.facts` : undefined} focusField="facts" label="事实" value={value.facts} onChange={(facts) => onChange({ ...value, facts })} />
    <EntityStateEditor focusKey={focusKey ? `${focusKey}.entityStates` : undefined} label="实体状态" value={value.entityStates} options={options} onChange={(entityStates) => onChange({ ...value, entityStates })} />
    <div className="field-grid two compact">
      <Field label="画面方向"><input data-focus-key={focusKey ? `${focusKey}.screenDirection` : undefined} value={value.screenDirection ?? ""} onChange={(event) => onChange({ ...value, screenDirection: event.target.value || null })} /></Field>
      <Field label="光线"><input data-focus-key={focusKey ? `${focusKey}.lighting` : undefined} value={value.lighting ?? ""} onChange={(event) => onChange({ ...value, lighting: event.target.value || null })} /></Field>
      <Field label="声音连续性"><input data-focus-key={focusKey ? `${focusKey}.sound` : undefined} value={value.sound ?? ""} onChange={(event) => onChange({ ...value, sound: event.target.value || null })} /></Field>
    </div>
    <div data-focus-key={focusKey ? `${focusKey}.notes` : undefined} tabIndex={focusKey ? -1 : undefined}><StringListEditor label="备注（每行一条）" value={value.notes} onChange={(notes) => onChange({ ...value, notes })} rows={2} /></div>
  </details>;
}
