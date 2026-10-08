import type { AcceptedScriptRevision, ProductionSceneMapping, Shot } from "../../types";
import { bridgeCut, type BridgeCut } from "../../production-bridge-handoff";
import { sourceSecondsToMilliseconds } from "../../production-timing";
import { sectionEpisode } from "./scriptProjection";

export interface NodeProductionScene { sceneId: string; episode: number; sceneIndex: number; title: string; cuts: Array<BridgeCut & { order: number }> }
const positiveInteger = (value: unknown): value is number => typeof value === "number" && Number.isInteger(value) && value > 0;

/** Current F4 occurrence coordinates and F5 identities must agree; never infer. */
export function nodeProductionScenes(proposal: ProductionSceneMapping, accepted: AcceptedScriptRevision, sectionId: string): NodeProductionScene[] {
  if (proposal.inputs.scriptRevision !== accepted.revision || proposal.inputs.scriptContentHash !== accepted.contentHash) throw new Error("投产映射使用的剧本版本已变化；原场次与媒体保留，请返回整包评审。");
  const episode = sectionEpisode(accepted.script, accepted.binding, sectionId);
  const scenes = proposal.scenes.filter(scene => scene.sectionId === sectionId);
  const cuts = proposal.cuts.filter(cut => cut.sectionId === sectionId);
  if (!episode) {
    if (scenes.length || cuts.length) throw new Error("路线控制仍有旧投产映射；保留旧媒体，当前不能作为无画面节点直达镜头。");
    return [];
  }
  if (scenes.length !== episode.scenes.length) throw new Error("投产场次与当前剧本出现次数不一致；不能猜测映射。");
  const identities = new Set<string>(), occurrences = new Set<number>(), sceneIds = new Set<string>(), coordinates = new Set<string>();
  const result = scenes.map(scene => {
    if (scene.episode !== episode.ep || !positiveInteger(scene.sceneIndex) || scene.sceneIndex > episode.scenes.length || occurrences.has(scene.sceneIndex)
      || typeof scene.sceneId !== "string" || !scene.sceneId || sceneIds.has(scene.sceneId) || scene.title !== episode.scenes[scene.sceneIndex - 1].sceneId || !positiveInteger(scene.cutCount)) throw new Error("投产场次缺少唯一的当前出现坐标。");
    occurrences.add(scene.sceneIndex); sceneIds.add(scene.sceneId);
    const selected = cuts.filter(cut => cut.sceneIndex === scene.sceneIndex).map(raw => {
      const cut = bridgeCut(raw);
      if (!cut || cut.episode !== scene.episode || cut.segmentSceneIndex !== scene.sceneIndex || !positiveInteger(raw.cutIndex) || identities.has(cut.shotId)) throw new Error("镜头来源坐标或身份不完整；直达已暂停。");
      const coordinate = JSON.stringify([cut.episode, cut.sceneIndex, cut.segmentIndex, cut.sourceCutIndex]);
      if (coordinates.has(coordinate)) throw new Error("多个镜头声称同一来源坐标；不能猜测映射。");
      coordinates.add(coordinate); identities.add(cut.shotId); return { ...cut, order: raw.cutIndex };
    }).sort((left, right) => left.order - right.order);
    if (selected.length !== scene.cutCount || selected.some((cut, index) => cut.order !== index + 1)) throw new Error("场次镜头数量或顺序与投产证据不一致。");
    return { sceneId: scene.sceneId, episode: scene.episode as number, sceneIndex: scene.sceneIndex, title: scene.title, cuts: selected };
  }).sort((left, right) => left.sceneIndex - right.sceneIndex);
  if (result.reduce((total, scene) => total + scene.cuts.length, 0) !== cuts.length) throw new Error("有镜头无法绑定当前场次；保留证据供检查。");
  return result;
}

export function installedCutMatches(cut: BridgeCut, sceneId: string, shot: Shot | undefined): boolean {
  return Boolean(shot && shot.id === cut.shotId && shot.sceneId === sceneId && shot.durationUnits === sourceSecondsToMilliseconds(cut.seconds));
}
