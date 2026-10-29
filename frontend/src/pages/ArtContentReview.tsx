import { record } from "./artReferencePresentation";

const records = (value: unknown): Record<string, unknown>[] => Array.isArray(value) ? value.map(record) : [];
const scaleLabels: Record<string, string> = { small: "小型", medium: "中型", large: "大型" };

/** Read projection of authored Art fields. Never writes or translates the source. */
export function ArtSubjectDescription({ content }: { content: Record<string, unknown> }) {
  const variants = [...records(content.lighting), ...records(content.states)];
  return <section className="art-subject-description">
    {typeof content.summary === "string" && <p>{content.summary}</p>}
    {typeof content.scale === "string" && <p>尺度：{scaleLabels[content.scale] || content.scale}</p>}
    {variants.map((variant, index) => <section key={String(variant.id || index)}>
      <strong>{String(variant.name || variant.label || variant.state || variant.id || `形态 ${index + 1}`)}</strong>
      <p>{typeof variant.description === "string" && variant.description ? variant.description : "此保留版本未提供独立创作描述。"}</p>
      {typeof variant.prompt === "string" && <details><summary>图像生成指令（技术详情，原文）</summary><pre>{variant.prompt}</pre></details>}
    </section>)}
  </section>;
}

export function ArtContentReview({ art }: { art: Record<string, unknown> }) {
  return <section aria-label="美术创作描述">
    {(["scenes", "props"] as const).map(key => <section key={key}>
      <h3>{key === "scenes" ? "地点设定" : "道具设定"}</h3>
      {records(art[key]).map((content, index) => <article key={String(content.id || index)}>
        <h4>{String(content.name || content.id || "未命名设定")}</h4>
        <ArtSubjectDescription content={content} />
      </article>)}
    </section>)}
  </section>;
}
