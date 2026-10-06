import { useEffect, useState } from "react";
import { plotloomApi } from "../../api";
import type { ProductionBridgeState, ScriptReviewState, StoryboardReview, WorkspaceProject } from "../../types";

interface ProductionRead { identity: string; bridge?: ProductionBridgeState; script?: ScriptReviewState; review?: StoryboardReview; errors: string[] }

/** Read models only. Existing review/media owners retain every write command. */
export function useCreatorProduction(project: WorkspaceProject, bindingHash: string | undefined, active: boolean) {
  const [attempt, setAttempt] = useState(0), [read, setRead] = useState<ProductionRead>();
  const identity = JSON.stringify([project.id, project.revision, project.stageRevisions.story_graph, project.stageRevisions.storyboard, bindingHash, active, attempt]);
  useEffect(() => {
    if (!project.id) return;
    const controller = new AbortController();
    void Promise.allSettled([
      plotloomApi.getProductionBridge(project.id, controller.signal),
      active ? plotloomApi.getScript(project.id) : Promise.resolve(null),
      active ? plotloomApi.getStoryboardReview(project.id, controller.signal) : Promise.resolve(null),
    ]).then(([bridge, script, review]) => {
      if (controller.signal.aborted) return;
      setRead({ identity, bridge: bridge.status === "fulfilled" ? bridge.value : undefined,
        script: script.status === "fulfilled" && script.value ? script.value : undefined,
        review: review.status === "fulfilled" && review.value ? review.value : undefined,
        errors: [bridge.status === "rejected" && "投产映射暂不可读取", script.status === "rejected" && "剧本暂不可读取", review.status === "rejected" && "分镜审核暂不可读取"].filter(Boolean) as string[] });
    });
    return () => controller.abort();
  }, [identity]);
  return { data: read?.identity === identity ? read : undefined, retry: () => setAttempt(value => value + 1) };
}
