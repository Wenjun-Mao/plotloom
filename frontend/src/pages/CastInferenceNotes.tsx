import { castTextPresentation } from "./cast-text-presentation";

export function CastInferenceNotes({ character }: { character: Record<string, unknown> }) {
  const persona = record(character.persona);
  const traits = Array.isArray(persona.personality) ? persona.personality : [];
  const fields = [
    ...traits.map((value, index) => ({ label: `性格特点 ${index + 1}`, value })),
    { label: "气质与举止", value: persona.temperament },
    { label: "外观", value: persona.appearance },
    { label: "声音方向", value: record(character.voice).timbre },
  ].filter(({ value }) => castTextPresentation(value).annotation);
  if (!fields.length) return null;
  return <details className="cast-inference-notes">
    <summary>查看推断说明（{fields.length}）</summary>
    <p>以下内容带有推断标注，供你审核。标注集中显示在这里，保存时仍会保留；正文中的说明不会自动改写。</p>
    <dl>{fields.map(({ label, value }) => <div key={label}><dt>{label}</dt><dd>{String(value)}</dd></div>)}</dl>
  </details>;
}

function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }
