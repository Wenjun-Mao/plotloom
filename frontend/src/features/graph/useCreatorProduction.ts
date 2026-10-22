import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import type { ProductionBridgeState, ScriptReviewState, StoryboardReview, StoryboardReviewState, WorkspaceProject } from "../../types";

export interface ProductionRead { identity: string; bridge?: ProductionBridgeState; script?: ScriptReviewState; storyboardSource?: StoryboardReviewState; review?: StoryboardReview; errors: string[] }

/** Read models only. Existing review/media owners retain every write command. */
export function useCreatorProduction(project: WorkspaceProject, bindingHash: string | undefined, active: boolean) {
  const [attempt, setAttempt] = useState(0), [read, setRead] = useState<{ owner: object; data: ProductionRead }>();
  const identity = JSON.stringify([project.id, project.revision, project.stageRevisions.story_graph, project.stageRevisions.storyboard, bindingHash, active, attempt]);
  const owner = useRef({ identity });
  // A → B → A and leaving/re-entering review pages must not revive an old read.
  if (owner.current.identity !== identity) owner.current = { identity };
  useEffect(() => {
    if (!project.id || !active) return;
    const request = owner.current;
    const controller = new AbortController();
    void Promise.allSettled([
      plotloomApi.getProductionBridge(project.id, controller.signal),
      plotloomApi.getScript(project.id),
      plotloomApi.getStoryboardSourceReview(project.id),
      plotloomApi.getStoryboardReview(project.id, controller.signal),
    ]).then(([bridge, script, storyboardSource, review]) => {
      if (controller.signal.aborted || request !== owner.current) return;
      setRead({ owner: request, data: { identity, bridge: bridge.status === "fulfilled" ? bridge.value : undefined,
        script: script.status === "fulfilled" && script.value ? script.value : undefined,
        storyboardSource: storyboardSource.status === "fulfilled" ? storyboardSource.value : undefined,
        review: review.status === "fulfilled" && review.value ? review.value : undefined,
        // Source-storyboard advice does not add a new shot-operation gate.
        errors: [bridge.status === "rejected" && "投产映射暂不可读取", script.status === "rejected" && "剧本暂不可读取", review.status === "rejected" && "分镜审核暂不可读取"].filter(Boolean) as string[] } });
    });
    return () => controller.abort();
  }, [identity]);
  return { data: read?.owner === owner.current ? read.data : undefined, retry: () => setAttempt(value => value + 1) };
}
