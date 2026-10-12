import type { ScriptBinding } from "../../types";
import { sectionEpisode, type ScriptEpisode } from "./scriptProjection";

type ScriptContentReviewProps = {
  title: string;
  statusDescription?: string;
  script: Record<string, unknown> | null;
  binding: ScriptBinding;
  sectionId?: string;
};

/** Renders only content linked by this object's frozen Script binding. */
export function ScriptContentReview({ title, statusDescription, script, binding, sectionId }: ScriptContentReviewProps) {
  return <section className="script-content-review" aria-label={title} data-testid="script-content-review">
    <h3>{title}</h3>
    {statusDescription && <p className="script-content-status">{statusDescription}</p>}
    {script === null
      ? <Mismatch message="此对象标记为可审阅，但 script 内容为空；未从其他版本推断内容。" raw={script} />
      : sectionId
        ? <BoundSection script={script} binding={binding} sectionId={sectionId} />
        : <BoundChapters script={script} binding={binding} />}
    <details className="script-json-disclosure">
      <summary>查看此对象的冻结绑定与完整原始剧本 JSON</summary>
      <h4>冻结章节绑定</h4><pre>{JSON.stringify(binding, null, 2)}</pre>
      <h4>原始剧本 JSON</h4><pre>{JSON.stringify(script, null, 2) ?? String(script)}</pre>
    </details>
  </section>;
}

/** Shows the one authored chapter draft without changing its stored binding. */
export function ScriptDraftEpisodeReview({ title, text, binding, sectionId }: {
  title: string;
  text: string;
  binding: ScriptBinding;
  sectionId: string;
}) {
  let episode: ScriptEpisode;
  try {
    const draftEpisode: unknown = JSON.parse(text);
    if (binding.routeOnlySectionIds.includes(sectionId)) {
      return <section className="script-content-review" aria-label={title} data-testid="script-content-review">
        <h3>{title}</h3><Mismatch message="此节点在基准绑定中是路线控制点，没有可编辑场次；保留的草稿原文仍可检查。" raw={text} />
      </section>;
    }
    const projected = sectionEpisode({ episodes: [draftEpisode] }, binding, sectionId);
    if (!projected) throw new Error("此节点在基准绑定中是路线控制点，没有画面场次。");
    episode = projected;
  } catch (reason) {
    return <section className="script-content-review" aria-label={title} data-testid="script-content-review">
      <h3>{title}</h3><Mismatch message={`草稿暂时无法按基准绑定阅读：${errorText(reason)} 原始草稿仍保留在编辑框中。`} raw={text} />
    </section>;
  }
  return <section className="script-content-review" aria-label={title} data-testid="script-content-review">
    <h3>{title}</h3>
    <p className="script-content-status">此视图按基准版本的冻结绑定读取所选章节；保存仍需使用现有章节编辑操作。</p>
    <ScriptEpisodeReading episode={episode} sectionId={sectionId} />
    <details className="script-json-disclosure"><summary>查看未保存草稿的原始章节 JSON</summary><pre>{text}</pre></details>
  </section>;
}

function BoundSection({ script, binding, sectionId }: { script: Record<string, unknown>; binding: ScriptBinding; sectionId: string }) {
  if (binding.routeOnlySectionIds.includes(sectionId)) return <p className="script-content-status">此节点按本对象的冻结绑定是路线控制点，没有自己的画面场次。</p>;
  try {
    const episode = sectionEpisode(script, binding, sectionId);
    if (!episode) return <p className="script-content-status">此节点按本对象的冻结绑定没有自己的画面场次。</p>;
    return <ScriptEpisodeReading episode={episode} sectionId={sectionId} />;
  } catch (reason) {
    return <Mismatch message={`无法按此对象的冻结绑定读取章节：${errorText(reason)}`} raw={script} />;
  }
}

function BoundChapters({ script, binding }: { script: Record<string, unknown>; binding: ScriptBinding }) {
  const rawEpisodes = script.episodes;
  if (!Array.isArray(rawEpisodes)) return <Mismatch message="此剧本没有可读取的 episodes 数组；原始内容仍可检查。" raw={script} />;
  const displayed = new Set<string>();
  return <>
    {rawEpisodes.length === 0 && <p className="script-content-status">原始剧本没有章节。</p>}
    {rawEpisodes.map((rawEpisode, index) => {
      if (!isRecord(rawEpisode) || typeof rawEpisode.ep !== "number") {
        return <Mismatch key={`raw:${index}`} message={`原始章节 ${index + 1} 缺少可核对的 episode 标识；未猜测章节映射。`} raw={rawEpisode} />;
      }
      const matches = binding.sectionBindings.filter(item => item.episode === rawEpisode.ep);
      if (matches.length !== 1) {
        return <Mismatch key={`episode:${index}`} message={`原始 episode ${rawEpisode.ep} 在此对象的冻结绑定中对应 ${matches.length} 个章节，无法唯一确认归属。`} raw={rawEpisode} />;
      }
      const section = matches[0];
      displayed.add(section.sectionId);
      if (binding.routeOnlySectionIds.includes(section.sectionId)) {
        return <Mismatch key={`episode:${index}`} message={`冻结绑定将 ${section.sectionId} 标为路线控制点，却在原始剧本中发现 episode ${rawEpisode.ep}；未把它当作可播放场次。`} raw={rawEpisode} />;
      }
      try {
        const episode = sectionEpisode(script, binding, section.sectionId);
        if (!episode || episode !== rawEpisode) throw new Error("章节原文未能唯一对应到冻结绑定。");
        return <ScriptEpisodeReading key={`episode:${index}`} episode={episode} sectionId={section.sectionId} />;
      } catch (reason) {
        return <Mismatch key={`episode:${index}`} message={`章节 ${section.sectionId} · episode ${rawEpisode.ep} 无法按冻结绑定读取：${errorText(reason)}`} raw={rawEpisode} />;
      }
    })}
    {binding.sectionBindings.map((item, index) => {
      if (displayed.has(item.sectionId) || binding.routeOnlySectionIds.includes(item.sectionId)) return null;
      const hasEpisode = rawEpisodes.some(value => isRecord(value) && value.ep === item.episode);
      if (hasEpisode) return null;
      return <Mismatch key={`missing:${item.sectionId}:${index}`} message={`冻结绑定中的章节 ${item.sectionId} · episode ${item.episode} 在原始剧本中缺失。`} raw={script} />;
    })}
    {binding.routeOnlySectionIds.length > 0 && <section className="script-route-controls" aria-label="冻结绑定中的路线控制节点">
      <h4>路线控制节点 · 没有自己的画面场次</h4>
      <ul>{binding.routeOnlySectionIds.map(section => <li key={section}>{section} · 本对象的冻结绑定明确标为仅控制路线</li>)}</ul>
    </section>}
  </>;
}

function ScriptEpisodeReading({ episode, sectionId }: { episode: ScriptEpisode; sectionId: string }) {
  const targetSeconds = episode.targetSeconds;
  return <article className="script-readable-episode" data-script-episode={episode.ep} data-script-section={sectionId}>
    <header><h4>章节 {sectionId} · episode {episode.ep}</h4>
      {typeof targetSeconds === "number" && <p className="script-content-status">章节计划画面时长 {targetSeconds} 秒；这是创作计划，不是最终运行时间，互斥结局不会合计。</p>}
    </header>
    {episode.scenes.map((scene, index) => {
      const validCharacters = Array.isArray(scene.characters) && scene.characters.every(value => typeof value === "string");
      const validProps = scene.props === undefined || (Array.isArray(scene.props) && scene.props.every(value => typeof value === "string"));
      const validLighting = scene.lighting === undefined || typeof scene.lighting === "string";
      const validFlow = Array.isArray(scene.flow) && scene.flow.every(isRecord);
      return <section className="script-readable-scene" key={`${sectionId}:${episode.ep}:${index + 1}`} data-script-occurrence={`${sectionId}:${episode.ep}:${index + 1}`}>
        <h5>场次 {index + 1} · {scene.sceneId}</h5>
        <p className="script-scene-context">
          光线：{typeof scene.lighting === "string" ? scene.lighting : "未提供"} · 人物：{validCharacters ? scene.characters.join("、") || "空镜" : "字段无法读取"} · 道具：{validProps ? scene.props?.join("、") || "无" : "字段无法读取"}
        </p>
        {(!validCharacters || !validProps || !validLighting || !validFlow) && <Mismatch message="此场次有字段不符合可读结构；下面的原始场次 JSON 保留了原文。" raw={scene} />}
        {validFlow && scene.flow.map((item, order) => <ReadableFlowItem key={`${sectionId}:${episode.ep}:${index + 1}:${order + 1}`} item={item} order={order} />)}
        <details className="script-json-disclosure"><summary>查看完整场次字段</summary><pre>{JSON.stringify(scene, null, 2)}</pre></details>
      </section>;
    })}
    <details className="script-json-disclosure"><summary>查看完整章节字段</summary><pre>{JSON.stringify(episode, null, 2)}</pre></details>
  </article>;
}

function ReadableFlowItem({ item, order }: { item: Record<string, unknown>; order: number }) {
  const hasAction = typeof item.action === "string";
  const hasLine = typeof item.line === "string";
  const speakerValid = item.speaker === undefined || typeof item.speaker === "string";
  const deliveryValid = item.delivery === undefined || typeof item.delivery === "string";
  if (!hasAction && !hasLine) return <Mismatch message={`叙事顺序 ${order + 1} 没有可识别的 action 或 line 字段。`} raw={item} />;
  return <div className="script-readable-flow" data-flow-order={order + 1}>
    {hasAction && <p className="script-readable-action">{item.action as string}</p>}
    {hasLine && <p className="script-readable-dialogue"><strong>{speakerValid ? (typeof item.speaker === "string" ? item.speaker : "（未提供说话者）") : "（说话者字段无法读取）"}：</strong>{item.line as string}{typeof item.delivery === "string" && <small> · {item.delivery}</small>}</p>}
    {(!speakerValid || !deliveryValid) && <Mismatch message={`叙事顺序 ${order + 1} 的说话者或表达方式无法按文本读取；原始段落仍可检查。`} raw={item} />}
  </div>;
}

function Mismatch({ message, raw }: { message: string; raw: unknown }) {
  const inspectableRaw = typeof raw === "string" ? raw : JSON.stringify(raw, null, 2) ?? String(raw);
  return <section className="script-content-mismatch" role="note">
    <p>{message}</p><details className="script-json-disclosure"><summary>检查对应原始数据</summary><pre>{inspectableRaw}</pre></details>
  </section>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function errorText(reason: unknown): string {
  return reason instanceof Error ? reason.message : String(reason);
}
