import { useId } from "react";
import { CastInferenceNotes } from "./CastInferenceNotes";
import { castTextPresentation, editCastText } from "./cast-text-presentation";
import { CastFieldLabel } from "./CastFieldLabel";

export type CastDirectionChange = (...args:
  | [index: number, group: "persona", key: "personality", value: string[]]
  | [index: number, group: "persona", key: "temperament" | "appearance", value: string]
  | [index: number, group: "voice", key: "timbre", value: string]
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
        <CastInferenceNotes character={character} />
      </fieldset>;
    })}
  </section>;
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
