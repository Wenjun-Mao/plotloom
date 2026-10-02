import { useId } from "react";
import { CastInferenceNotes } from "./CastInferenceNotes";
import { castTextPresentation, editCastText } from "./cast-text-presentation";
import { CastFieldLabel } from "./CastFieldLabel";
import { castDesignErrors } from "./cast-design-validation";

export type CastDirectionChange = (...args:
  | [index: number, group: "persona", key: "personality", value: string[]]
  | [index: number, group: "persona", key: "temperament" | "appearance", value: string]
  | [index: number, group: "voice", key: "timbre", value: string]
  | [index: number, group: "image", key: "style" | "prompt" | "promptLocal" | "negativePrompt" | "sheet", value: string]
  | [index: number, group: "image", key: "tags", value: string[]]
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
    <p className="cast-field-requirements">带 * 的为必填项，其余可留空。每个角色至少填写一个性格特点，并提供外观描述；已有的设定依据建议保留。</p>
    {characters.map((character, index) => {
      const persona = record(character.persona);
      const traits = Array.isArray(persona.personality) ? persona.personality as string[] : [];
      const fieldId = `${editorId}-${index}`;
      const errors = castDesignErrors(character);
      return <fieldset key={String(character.id || index)}>
        <legend>{String(character.name || character.id || `角色 ${index + 1}`)}</legend>
        <div className="cast-personality" role="group" aria-label="性格特点（必填，至少一项）">
          <strong>性格特点 <span aria-hidden="true">*</span></strong>
          <p id={`${fieldId}-traits-help`}>至少填写一项。</p>
          {errors.personality && <p id={`${fieldId}-traits-error`} role="alert">{errors.personality}</p>}
          <div className="cast-traits">
            {traits.map((trait, traitIndex) => <div className="cast-trait" key={traitIndex}>
              <div className="cast-design-field">
                <CastFieldLabel htmlFor={`${fieldId}-trait-${traitIndex}`}>性格特点 {traitIndex + 1}</CastFieldLabel>
                <input id={`${fieldId}-trait-${traitIndex}`} aria-invalid={Boolean(errors.personality)} aria-describedby={`${fieldId}-traits-help${errors.personality ? ` ${fieldId}-traits-error` : ""}`} disabled={disabled} value={castTextPresentation(trait).text} onChange={(event) => onChange(index, "persona", "personality", traits.map((value, position) => position === traitIndex ? editCastText(value, event.target.value) : value))} />
              </div>
              <button type="button" disabled={disabled} aria-label={`删除性格特点 ${traitIndex + 1}`} onClick={() => onChange(index, "persona", "personality", traits.filter((_, position) => position !== traitIndex))}>删除</button>
            </div>)}
          </div>
          <button className="cast-add-trait" type="button" disabled={disabled} onClick={() => onChange(index, "persona", "personality", [...traits, ""])}>添加性格特点</button>
        </div>
        <CastDesignField id={`${fieldId}-temperament`} label="气质与举止" value={persona.temperament} disabled={disabled} onChange={(value) => onChange(index, "persona", "temperament", value)} />
        <CastDesignField id={`${fieldId}-appearance`} label="外观" required error={errors.appearance} value={persona.appearance} disabled={disabled} onChange={(value) => onChange(index, "persona", "appearance", value)} />
        <CastDesignField id={`${fieldId}-voice`} label="声音方向" value={record(character.voice).timbre} disabled={disabled} onChange={(value) => onChange(index, "voice", "timbre", value)} wide />
        <details className="cast-wide-field">
          <summary>角色图像方向</summary>
          <p>这些方向会与角色外观一起用于后续参考图任务。请明确修改所有冲突的风格描述；保存不会自动翻译、生成图片或改写美术设定。</p>
          {([
            ["style", "角色图像风格"], ["prompt", "角色图像提示词"],
            ["promptLocal", "角色图像中文提示词"], ["negativePrompt", "角色图像反向提示词"],
            ["sheet", "角色设定图提示词"],
          ] as const).map(([key, label]) => <CastDesignField key={key} id={`${fieldId}-image-${key}`} label={label} value={record(character.image)[key]} disabled={disabled} onChange={(value) => onChange(index, "image", key, value)} />)}
          <CastNoteField id={`${fieldId}-image-tags`} label="角色图像标签（每行一个）" value={Array.isArray(record(character.image).tags) ? (record(character.image).tags as string[]).join("\n") : ""} disabled={disabled} onChange={(value) => onChange(index, "image", "tags", value.split("\n").map((tag) => tag.trim()).filter(Boolean))} />
        </details>
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
function CastDesignField({ id, label, value, disabled, onChange, wide = false, required = false, error = "" }: {
  id: string; label: string; value: unknown; disabled: boolean; onChange: (value: string) => void; wide?: boolean; required?: boolean; error?: string;
}) {
  return <div className={`cast-design-field${wide ? " cast-wide-field" : ""}`}>
    <CastFieldLabel htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}</CastFieldLabel>
    <textarea id={id} rows={3} required={required} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} disabled={disabled} value={castTextPresentation(value).text} onChange={(event) => onChange(editCastText(value, event.target.value))} />
    {error && <p id={`${id}-error`} role="alert">{error}</p>}
  </div>;
}
