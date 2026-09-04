import { useState } from "react";
import type { CharacterCard, StoryBible } from "../types";
import { Button, Field, PageHeader, Panel } from "../components";

export function StoryBiblePage({ value, stale, saving, entityId, onEntitySelect, onSave, onDraftChange }: { value: StoryBible; stale: boolean; saving: boolean; entityId?: string; onEntitySelect?: (entityId: string) => void; onSave: (value: StoryBible) => Promise<void>; onDraftChange?: (value: StoryBible) => void }) {
  const [draft, setDraft] = useState(value);
  const update = (next: StoryBible | ((current: StoryBible) => StoryBible)) => setDraft((current) => { const updated = typeof next === "function" ? next(current) : next; onDraftChange?.(updated); return updated; });
  const selectCharacter = (id: string) => onEntitySelect?.(id);
  const updateCharacter = (id: string, patch: Partial<CharacterCard>) => {
    selectCharacter(id);
    update((current) => ({ ...current, characters: current.characters.map((card) => card.id === id ? { ...card, ...patch } : card) }));
  };
  const addCharacter = () => update((current) => ({ ...current, characters: [...current.characters, { id: crypto.randomUUID(), name: "新角色", role: "", description: "", goal: "", traits: [], continuityRules: [], visualAnchors: [], soundAnchors: [], voiceAnchors: [], allowedStates: [] }] }));
  return <div className="page">
    <PageHeader eyebrow="02 · Canon" title="故事圣经" description="人物、世界规则和视觉语言只在这里定义；场景与分镜引用它们。" actions={<><span className={`stage-chip ${stale ? "stale" : "ready"}`}>{stale ? "上游已变更" : "当前版本"}</span><Button variant="primary" disabled={saving} onClick={() => void onSave(draft)}>{saving ? "正在保存…" : "保存故事圣经"}</Button></>} />
    <Panel className="form-card">
      <div className="field-grid two">
        <Field label="Logline"><textarea rows={4} value={draft.logline} onChange={(event) => update({ ...draft, logline: event.target.value })} /></Field>
        <Field label="故事前提"><textarea rows={4} value={draft.premise} onChange={(event) => update({ ...draft, premise: event.target.value })} /></Field>
        <Field label="统一视觉语言"><textarea rows={4} value={draft.visualLanguage} onChange={(event) => update({ ...draft, visualLanguage: event.target.value })} /></Field>
        <Field label="叙事承诺"><textarea rows={4} value={draft.narrativePromise} onChange={(event) => update({ ...draft, narrativePromise: event.target.value })} /></Field>
        <Field label="主题（每行一条）"><textarea rows={5} value={draft.themes.join("\n")} onChange={(event) => update({ ...draft, themes: event.target.value.split("\n").filter(Boolean) })} /></Field>
        <Field label="世界规则（每行一条）"><textarea rows={5} value={draft.worldRules.join("\n")} onChange={(event) => update({ ...draft, worldRules: event.target.value.split("\n").filter(Boolean) })} /></Field>
      </div>
    </Panel>
    <div className="section-bar"><div><span className="eyebrow">Character continuity</span><h2>角色卡</h2></div><Button variant="quiet" onClick={addCharacter}>＋ 新角色</Button></div>
    <div className="card-grid">
      {draft.characters.map((character, index) => <Panel className={`character-card ${character.id === entityId ? "selected" : ""}`} key={character.id}>
        <div onFocus={() => selectCharacter(character.id)}>
          <div className="card-index">{String(index + 1).padStart(2, "0")}</div>
          <Field label="姓名"><input value={character.name} onChange={(event) => updateCharacter(character.id, { name: event.target.value })} /></Field>
          <Field label="叙事职责"><input value={character.role || ""} onChange={(event) => updateCharacter(character.id, { role: event.target.value })} /></Field>
          <Field label="稳定外观"><textarea rows={3} value={character.visualAnchors.join("\n")} onChange={(event) => updateCharacter(character.id, { visualAnchors: event.target.value.split("\n").filter(Boolean) })} /></Field>
          <div className="field-grid two compact"><Field label="角色描述"><textarea rows={3} value={character.description} onChange={(event) => updateCharacter(character.id, { description: event.target.value })} /></Field><Field label="目标"><textarea rows={3} value={character.goal} onChange={(event) => updateCharacter(character.id, { goal: event.target.value })} /></Field></div>
          <Field label="连续性规则（每行一条）"><textarea rows={3} value={character.continuityRules.join("\n")} onChange={(event) => updateCharacter(character.id, { continuityRules: event.target.value.split("\n").filter(Boolean) })} /></Field>
          <div className="field-grid two compact"><Field label="视觉 anchors（每行一条）"><textarea rows={2} value={(character.visualAnchors || []).join("\n")} onChange={(event) => updateCharacter(character.id, { visualAnchors: event.target.value.split("\n").filter(Boolean) })} /></Field><Field label="声音 / 语音 anchors"><textarea rows={2} value={[...(character.soundAnchors || []), ...(character.voiceAnchors || [])].join("\n")} onChange={(event) => updateCharacter(character.id, { soundAnchors: event.target.value.split("\n").filter(Boolean) })} /></Field></div>
          <Field label="允许状态（每行一条）"><textarea rows={2} value={(character.allowedStates || []).join("\n")} onChange={(event) => updateCharacter(character.id, { allowedStates: event.target.value.split("\n").filter(Boolean) })} /></Field>
        </div>
      </Panel>)}
    </div>
  </div>;
}
