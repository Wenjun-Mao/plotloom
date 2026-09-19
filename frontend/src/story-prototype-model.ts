import { deriveRoutes, type StoryRoute } from "./model";
import type { ScriptBinding, ScriptReviewState, StageHead, StoryGraph } from "./types";

export type ScriptLine = { action?: string; speaker?: string; line?: string; delivery?: string };
export type PrototypeEpisode = {
  ep: number;
  targetSeconds?: number;
  hook?: string;
  cliff?: string;
  scenes?: Array<{
    sceneId?: string;
    lighting?: string;
    characters?: string[];
    props?: string[];
    flow?: ScriptLine[];
  }>;
};

export type PrototypeScript = {
  source?: string;
  lang?: string;
  sectionBindings?: Array<{ sectionId: string; episode: number }>;
  episodes?: PrototypeEpisode[];
};

export interface PrototypeRoute extends StoryRoute {
  sectionIds: string[];
}

/** Reject historical or edited script state rather than presenting it as current. */
export function prototypeReadiness(
  scriptStatus: ScriptReviewState["status"],
  graphHead: Pick<StageHead, "status" | "revision" | "contentHash"> | undefined,
  binding: Pick<ScriptBinding, "graphRevision" | "graphContentHash">,
): string | undefined {
  if (scriptStatus !== "accepted") return "当前剧本不是可阅读的已接受版本。请先在工作台完成当前版本的审核。";
  if (!graphHead || graphHead.status !== "ready") return "当前剧情图不可用或已过期。请先在工作台恢复规范剧情图。";
  if (graphHead.revision !== binding.graphRevision || graphHead.contentHash !== binding.graphContentHash) {
    return "剧本绑定的剧情图不是当前版本。请先处理工作台中的版本变更。";
  }
  return undefined;
}

/**
 * The graph remains the route authority. Script bindings only decide which
 * accepted episode is read for each canonical graph node.
 */
export function derivePrototypeRoutes(graph: StoryGraph, bindings: Array<{ sectionId: string; episode: number }>): PrototypeRoute[] {
  const boundSections = new Set(bindings.map((binding) => binding.sectionId));
  return deriveRoutes(graph)
    .filter((route) => route.nodeIds.every((nodeId) => boundSections.has(nodeId)))
    .map((route) => ({ ...route, sectionIds: route.nodeIds }));
}

export function episodeForSection(script: PrototypeScript, sectionId: string): PrototypeEpisode | undefined {
  const binding = script.sectionBindings?.find((item) => item.sectionId === sectionId);
  return script.episodes?.find((episode) => episode.ep === binding?.episode);
}

export function episodesForRoute(script: PrototypeScript, route: PrototypeRoute): Array<{ sectionId: string; episode: PrototypeEpisode }> {
  return route.sectionIds.flatMap((sectionId) => {
    const episode = episodeForSection(script, sectionId);
    return episode ? [{ sectionId, episode }] : [];
  });
}
