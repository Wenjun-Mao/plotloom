import type { ScriptBinding } from "../../types";

export interface ScriptScene extends Record<string, unknown> { sceneId: string; lighting?: string; characters: string[]; props?: string[]; flow: Array<Record<string, unknown>> }
export interface ScriptEpisode extends Record<string, unknown> { ep: number; scenes: ScriptScene[] }

/** This F4 binding owns section membership; raw episode fields stay intact. */
export function sectionEpisode(script: Record<string, unknown>, binding: ScriptBinding, sectionId: string): ScriptEpisode | null {
  if (binding.routeOnlySectionIds.includes(sectionId)) return null;
  const sections = binding.sectionBindings.filter(item => item.sectionId === sectionId);
  if (sections.length !== 1) throw new Error("此节点尚未绑定这份剧本中的唯一章节。请先确认图并重新审阅剧本。");
  if (!Array.isArray(script.episodes)) throw new Error("这份剧本缺少 episodes，不能建立章节映射。");
  const matches = script.episodes.filter(value => value && typeof value === "object" && value.ep === sections[0].episode);
  if (matches.length !== 1) throw new Error("这份剧本的章节绑定不唯一或缺失。");
  const episode = matches[0] as ScriptEpisode;
  if (!Array.isArray(episode.scenes) || episode.scenes.some(scene => !scene || typeof scene.sceneId !== "string" || !Array.isArray(scene.characters) || !Array.isArray(scene.flow))) throw new Error("这份剧本的章节场次结构不完整，保留原始内容供检查。");
  return episode;
}
