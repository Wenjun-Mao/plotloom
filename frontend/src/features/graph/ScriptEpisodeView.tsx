import type { AcceptedScriptRevision } from "../../types";
import { sectionEpisode } from "./scriptProjection";

export function ScriptEpisodeView({ accepted, sectionId }: { accepted: AcceptedScriptRevision; sectionId: string }) {
  try {
    const episode = sectionEpisode(accepted.script, accepted.binding, sectionId);
    if (!episode) return <p>当前已确认剧本将此节点作为路线控制，没有画面场次。若要包含画面，请先明确确认图内容，再重新审阅整份剧本。</p>;
    return <section aria-label="当前节点的剧本场次"><p>章节 {sectionId} · episode {episode.ep} · 剧本 r{accepted.revision} · {episode.scenes.length} 个场次</p>
      {episode.scenes.map((scene, index) => <details key={`${sectionId}:${episode.ep}:${index + 1}`} data-script-occurrence={`${sectionId}:${episode.ep}:${index + 1}`}><summary>场次 {index + 1} · {scene.sceneId}</summary>
        <p>{scene.lighting && <>光线 {scene.lighting} · </>}角色 {scene.characters.join("、") || "空镜"} · 道具 {scene.props?.join("、") || "无"}</p>
        {scene.flow.map((item, order) => <p key={`${sectionId}:${episode.ep}:${index + 1}:${order + 1}`}>{typeof item.action === "string" && item.action}{typeof item.line === "string" && <><strong>{String(item.speaker)}：</strong>{item.line}{typeof item.delivery === "string" && <small> · {item.delivery}</small>}</>}</p>)}
        <details><summary>完整场次字段</summary><pre>{JSON.stringify(scene, null, 2)}</pre></details>
      </details>)}
      <details><summary>完整章节字段</summary><pre>{JSON.stringify(episode, null, 2)}</pre></details>
    </section>;
  } catch (reason) { return <p className="notice warning">{String(reason)}</p>; }
}
