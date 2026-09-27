import { useId } from "react";
import { CastInferenceNotes } from "./CastInferenceNotes";
import { castTextPresentation, editCastText } from "./cast-text-presentation";
import { CastFieldLabel } from "./CastFieldLabel";

export type CastDirectionChange = (...args:
  | [index: number, group: "persona", key: "personality", value: string[]]
  | [index: number, group: "persona", key: "temperament" | "appearance", value: string]
  | [index: number, group: "voice", key: "timbre", value: string]
  | [index: number, group: "reviewNotes", key: "sourceNotes" | "performanceGuidance", value: string]
) => void;

export function CastEditor({ characters, disabled, onChange, editing = false }: {
  characters: Array<Record<string, unknown>>;
  disabled: boolean;
  onChange: CastDirectionChange;
  editing?: boolean;
}) {
  const editorId = useId();
  return <section className="cast-forms">
    <strong>{editing ? "编辑角色设定" : "审核并编辑角色设定"}</strong>
    <p className="cast-field-requirements">带 * 的为必填项，其余可留空。本页文字字段均可留空；已有的设定依据建议保留，方便审核创作补充。</p>
    {characters.map((character, index) => {
      const persona = record(character.persona);
      const traits = Array.isArray(persona.personality) ? persona.personality as string[] : [];
      const fieldId = `${editorId}-${index}`;
      return <fieldset key={String(character.id || index)}>
        <legend>{String(character.name || character.id || `角色 ${index + 1}`)}</legend>
        <div className="cast-personality">
          <strong>性格特点</strong>
          <div className="cast-traits">
            {traits.map((trait, traitIndex) => <div className="cast-trait" key={traitIndex}>
              <div className="cast-design-field">
                <CastFieldLabel htmlFor={`${fieldId}-trait-${traitIndex}`}>性格特点 {traitIndex + 1}</CastFieldLabel>
                <input id={`${fieldId}-trait-${traitIndex}`} disabled={disabled} value={castTextPresentation(trait).text} onChange={(event) => onChange(index, "persona", "personality", traits.map((value, position) => position === traitIndex ? editCastText(value, event.target.value) : value))} />
              </div>
              <button type="button" disabled={disabled} aria-label={`删除性格特点 ${traitIndex + 1}`} onClick={() => onChange(index, "persona", "personality", traits.filter((_, position) => position !== traitIndex))}>删除</button>
            </div>)}
          </div>
          <button className="cast-add-trait" type="button" disabled={disabled} onClick={() => onChange(index, "persona", "personality", [...traits, ""])}>添加性格特点</button>
        </div>
        <CastDesignField id={`${fieldId}-temperament`} label="气质与举止" value={persona.temperament} disabled={disabled} onChange={(value) => onChange(index, "persona", "temperament", value)} />
        <CastDesignField id={`${fieldId}-appearance`} label="外观" value={persona.appearance} disabled={disabled} onChange={(value) => onChange(index, "persona", "appearance", value)} />
        <CastDesignField id={`${fieldId}-voice`} label="声音方向" value={record(character.voice).timbre} disabled={disabled} onChange={(value) => onChange(index, "voice", "timbre", value)} wide />
        <CastInferenceNotes character={character} includeStructured={false} />
        <details className="cast-wide-field">
          <summary>设定说明与表演提示</summary>
          <p>说明哪些细节来自原文、哪些是创作补充；具体场景的表演要求单独记录。不会自动改写上方描述。</p>
          <CastNoteField id={`${fieldId}-source-notes`} label="设定依据与补充说明" value={record(character.reviewNotes).sourceNotes} disabled={disabled} onChange={(value) => onChange(index, "reviewNotes", "sourceNotes", value)} />
          <CastNoteField id={`${fieldId}-performance`} label="表演提示" value={record(character.reviewNotes).performanceGuidance} disabled={disabled} onChange={(value) => onChange(index, "reviewNotes", "performanceGuidance", value)} />
        </details>
      </fieldset>;
    })}
  </section>;
}

function CastNoteField({ id, label, value, disabled, onChange }: {
  id: string; label: string; value: unknown; disabled: boolean; onChange: (value: string) => void;
}) {
  return <div className="cast-design-field">
    <CastFieldLabel htmlFor={id}>{label}</CastFieldLabel>
    <textarea id={id} rows={3} disabled={disabled} value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)} />
  </div>;
}

function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }
function CastDesignField({ id, label, value, disabled, onChange, wide = false }: {
  id: string; label: string; value: unknown; disabled: boolean; onChange: (value: string) => void; wide?: boolean;
}) {
  return <div className={`cast-design-field${wide ? " cast-wide-field" : ""}`}>
    <CastFieldLabel htmlFor={id}>{label}</CastFieldLabel>
    <textarea id={id} rows={3} disabled={disabled} value={castTextPresentation(value).text} onChange={(event) => onChange(editCastText(value, event.target.value))} />
  </div>;
}
