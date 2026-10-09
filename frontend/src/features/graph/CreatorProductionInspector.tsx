import { Button } from "../../components";
import { currentBridgeCut } from "../../production-bridge-handoff";
import type { WorkspaceProject } from "../../types";
import type { CreatorNavigate } from "./CreatorWorkbench";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import { installedCutMatches, nodeProductionScenes, type NodeProductionScene } from "./productionProjection";
import type { useCreatorProduction } from "./useCreatorProduction";

export function CreatorProductionInspector({ project, read, graphCurrent, disabled, onNavigate, onOpenShot }: {
  project: WorkspaceProject; read: ReturnType<typeof useCreatorProduction>; graphCurrent: boolean; disabled: boolean;
  onNavigate: CreatorNavigate; onOpenShot: (shotId: string) => void;
}) {
  const owner = useGraphWorkbench(), sectionId = owner.selectedNodeId;
  const data = read.data, bridge = data?.bridge, script = data?.script, accepted = script?.acceptedScript;
  let scenes: NodeProductionScene[] = [], projectionError = "";
  const installation = bridge?.installation;
  const mapping = installation ?? bridge?.proposal;
  if (mapping && accepted && sectionId) {
    try { scenes = nodeProductionScenes(mapping, accepted, sectionId); }
    catch (reason) { projectionError = reason instanceof Error ? reason.message : String(reason); }
  }
  const current = graphCurrent && data?.errors.length === 0 && accepted && script?.acceptedReviewState.status === "current" && installation?.status === "current" && installation.staleReasons.length === 0 && !projectionError;
  const review = data?.review, revision = project.stageRevisions.storyboard;
  const approved = current && review?.head.status === "ready" && review.head.revision === revision && review.activeApproval?.subjectRevision === revision;
  return <section data-testid="creator-production">
    <p>当前节点的场次与镜头来自已确认剧本和投产映射。整包评审与安装、逐镜头批准、参考、关键帧和视频审核分别由原工作台处理。</p>
    <Button onClick={() => onNavigate("source", "storyboard-review")}>分镜与投产整包评审</Button><p>准备、审阅并确认整份投产提案；不会自动生成或选择媒体。</p>
    {!data && <p role="status">正在核对当前制作来源…</p>}
    {data?.errors.length ? <p className="notice warning">{data.errors.join("；")}。现有内容保留，状态未知。</p> : null}
    <Button variant="quiet" onClick={read.retry}>重新核对制作来源</Button>
    {!graphCurrent && <p className="notice warning">图草稿与当前已应用路线不同，或来源仍需确认。保留已安装镜头与媒体；此处的镜头直达暂不可用。</p>}
    {script && script.acceptedReviewState.status !== "current" && <p className="notice warning">{script.acceptedReviewState.status === "reopened" ? "剧本正在编辑" : accepted ? "保留的已确认剧本暂不能用于当前制作" : "尚无当前已确认剧本"}；请先返回故事页完成审阅。</p>}
    {!mapping && data && <p>尚未建立投产映射。请先确认整份剧本与分镜，再进入整包评审。</p>}
    {bridge?.status === "stale" && <p className="notice warning">投产来源已变化，旧映射与媒体仍保留。请核对整包评审；镜头直达已暂停。</p>}
    {!installation && bridge?.proposal && bridge.status === "ready" && <p>提案待审阅与明确确认；以下是候选映射，不能作为已建立的镜头操作。</p>}
    {installation?.status === "outdated" && <p>当前制作内容需要重建。请完成故事修改和来源评审，再到整包评审准备重建提案；旧镜头与媒体保留。</p>}
    {installation?.status === "current" && bridge?.status === "ready" && <p>新的制作提案尚未确认。以下仍是当前已建立的镜头，不是待审提案中的镜头。</p>}
    {projectionError && <p className="notice warning">{projectionError}</p>}
    {accepted && sectionId && !projectionError && accepted.binding.routeOnlySectionIds.includes(sectionId) && <p>{script?.acceptedReviewState.status === "current" ? "当前已确认剧本" : "保留的已确认剧本"} r{accepted.revision} 将此节点作为路线控制，无需拍摄；没有剧本场次、镜头或节点视频。包含画面须明确确认图，再重新审阅剧本与投产。</p>}
    {scenes.map(scene => <details key={scene.sceneId} open data-production-scene={scene.sceneId}><summary>场次 {scene.sceneIndex} · {scene.title} · {scene.cuts.length} 个镜头</summary>
      {scene.cuts.map(cut => {
        const shot = project.storyboard.shots.find(shot => shot.id === cut.shotId);
        const bound = current && Boolean(currentBridgeCut(bridge, revision, cut.shotId)) && installedCutMatches(cut, scene.sceneId, shot);
        return <article key={cut.shotId} className="creator-production-cut" data-production-shot={cut.shotId}>
          <strong>镜头 {cut.order} · {cut.seconds} 秒</strong><p>{shot?.title || "候选投产镜头"}</p>
          <p>{bound ? "当前已安装绑定" : "未安装、过期或镜头版本不同"} · 分镜{approved && bound ? "已批准" : "需审核"}</p>
          <Button disabled={disabled || !bound} onClick={() => onOpenShot(cut.shotId)}>镜头审核与媒体</Button>
          <small>打开此镜头的参考、关键帧候选与审核、视频候选及明确选择。这里不推断媒体就绪。</small>
          <details><summary>精确来源与身份</summary><p>{sectionId} · episode {cut.episode} · 场次 {cut.sceneIndex} · 段 {cut.segmentIndex} · 段内镜头 {cut.sourceCutIndex}</p><code>{cut.shotId}</code></details>
        </article>;
      })}
    </details>)}
  </section>;
}
