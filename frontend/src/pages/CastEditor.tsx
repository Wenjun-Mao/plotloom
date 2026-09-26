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
  return <section className="cast-forms">
    <strong>{editing ? "编辑角色设定" : "审核并编辑角色设定"}</strong>
    {characters.map((character, index) => {
      const persona = record(character.persona);
      const traits = Array.isArray(persona.personality) ? persona.personality as string[] : [];
      return <fieldset key={String(character.id || index)}>
        <legend>{String(character.name || character.id || `角色 ${index + 1}`)}</legend>
        <div className="cast-personality">
          <strong>性格与气质</strong>
          {traits.map((trait, traitIndex) => <div className="cast-trait" key={traitIndex}>
            <label>性格特点 {traitIndex + 1}<input disabled={disabled} value={trait} onChange={(event) => onChange(index, "persona", "personality", traits.map((value, position) => position === traitIndex ? event.target.value : value))} /></label>
            <button type="button" disabled={disabled} aria-label={`删除性格特点 ${traitIndex + 1}`} onClick={() => onChange(index, "persona", "personality", traits.filter((_, position) => position !== traitIndex))}>删除</button>
          </div>)}
          <button type="button" disabled={disabled} onClick={() => onChange(index, "persona", "personality", [...traits, ""])}>添加性格特点</button>
          <label>气质与举止<textarea disabled={disabled} value={text(persona.temperament)} onChange={(event) => onChange(index, "persona", "temperament", event.target.value)} /></label>
        </div>
        <label>外观<textarea disabled={disabled} value={text(persona.appearance)} onChange={(event) => onChange(index, "persona", "appearance", event.target.value)} /></label>
        <label>声音方向<textarea disabled={disabled} value={text(record(character.voice).timbre)} onChange={(event) => onChange(index, "voice", "timbre", event.target.value)} /></label>
      </fieldset>;
    })}
  </section>;
}

function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }
function text(value: unknown): string { return typeof value === "string" ? value : ""; }
