import { cameraLabel, shotSizeLabel } from "./storyboard-presentation";

type Raw = Record<string, unknown>;

function records(value: unknown): Raw[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is Raw => !!item && typeof item === "object");
}

function names(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return "无";
  return value.map(String).join(", ");
}

/** Displays the admitted upstream fields without constructing product shots or parsing H3. */
export function StoryboardReviewInspection({ title, value }: { title: string; value: Raw | null }) {
  return <details><summary>{title}</summary><section className="source-outline-json">
    {records(value?.episodes).map(episode => <section key={String(episode.ep)} data-episode={String(episode.ep)}>
      <strong>章节 {String(episode.ep)}</strong>
      {records(episode.segments).map(segment => <Segment key={String(segment.id)} value={segment} />)}
    </section>)}
    <details><summary>查看原始 JSON</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>
  </section></details>;
}

function Segment({ value }: { value: Raw }) {
  const cuts = records(value.cuts);
  return <section>
    <p>{String(value.id)} · 来源场景 {String(value.sceneIndex)} · {cuts.map(cut => String(cut.seconds)).join(" + ")}s</p>
    <ol>{cuts.map((cut, index) => <Cut key={index} value={cut} />)}</ol>
    <details><summary>H3 生成说明（技术详情）</summary>
    <pre data-testid="storyboard-h3-direction">{String(value.h3Prompt ?? "")}</pre></details>
  </section>;
}

function Cut({ value }: { value: Raw }) {
  const beats = Array.isArray(value.beats) ? value.beats.map(String).join("–") : "未提供";
  return <li data-testid="storyboard-cut">
    <p>{String(value.seconds)}s · {shotSizeLabel(value.size)} · {cameraLabel(value.camera)} · 节拍 {beats}</p>
    <p>{typeof value.composition === "string" && value.composition ? value.composition : "此保留版本未提供独立画面描述，请查看原始生成指令。"}</p>
    {typeof value.frame === "string" && <details><summary>图像生成指令（技术详情，原文）</summary><pre>{value.frame}</pre></details>}
    <small>参考需求 · 人物： {names(value.characters)} · 道具： {names(value.props)}</small>
  </li>;
}
