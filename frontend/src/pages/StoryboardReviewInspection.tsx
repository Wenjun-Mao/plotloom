type Raw = Record<string, unknown>;

function records(value: unknown): Raw[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is Raw => !!item && typeof item === "object");
}

function names(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return "none";
  return value.map(String).join(", ");
}

/** Displays the admitted upstream fields without constructing product shots or parsing H3. */
export function StoryboardReviewInspection({ title, value }: { title: string; value: Raw | null }) {
  return <details><summary>{title}</summary><section className="source-outline-json">
    {records(value?.episodes).map(episode => <section key={String(episode.ep)} data-episode={String(episode.ep)}>
      <strong>Episode {String(episode.ep)}</strong>
      {records(episode.segments).map(segment => <Segment key={String(segment.id)} value={segment} />)}
    </section>)}
    <details><summary>查看原始 JSON</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>
  </section></details>;
}

function Segment({ value }: { value: Raw }) {
  const cuts = records(value.cuts);
  return <section>
    <p>{String(value.id)} · Source scene {String(value.sceneIndex)} · {cuts.map(cut => String(cut.seconds)).join(" + ")}s</p>
    <ol>{cuts.map((cut, index) => <Cut key={index} value={cut} />)}</ol>
    <p>H3 review direction · original dialogue and reference alignment</p>
    <pre data-testid="storyboard-h3-direction">{String(value.h3Prompt ?? "")}</pre>
  </section>;
}

function Cut({ value }: { value: Raw }) {
  const beats = Array.isArray(value.beats) ? value.beats.map(String).join("–") : "unavailable";
  return <li data-testid="storyboard-cut">
    <p>{String(value.seconds)}s · {String(value.size)} · {String(value.camera)} · Beats {beats}</p>
    <p>{String(value.frame ?? "Frame unavailable")}</p>
    <small>Reference needs · Characters: {names(value.characters)} · Props: {names(value.props)}</small>
  </li>;
}
