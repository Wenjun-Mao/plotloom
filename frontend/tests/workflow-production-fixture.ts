import type { ProductionRead } from "../src/features/graph/useCreatorProduction";
import type { ScriptBinding, SourceOutlineReviewState } from "../src/types";
import { bridgeState } from "./production-bridge-fixture";

export function workflowProductionFixture(source: SourceOutlineReviewState): ProductionRead {
  const admission = source.graphAdmission!;
  const binding: ScriptBinding = { sourceRevision: admission.sourceRevision, sourceContentHash: admission.sourceContentHash, outlineRevision: admission.outlineRevision,
    outlineContentHash: admission.outlineContentHash, sectionMapRevision: admission.sectionMapRevision,
    sectionMapContentHash: admission.sectionMapContentHash, graphRevision: admission.graphRevision,
    graphContentHash: admission.graphContentHash, sectionBindings: [{ sectionId: "opening", episode: 1 }],
    sectionIds: ["opening"], castRevision: 1, castContentHash: "cast", artRevision: 1, artContentHash: "art",
    targetPlaythroughSeconds: 30, routeBudgetHash: "route-budget", routeOnlySectionIds: [], completeRouteSectionIds: [["opening"]] };
  return { identity: "verified-production", errors: [], bridge: bridgeState(),
    script: { status: "accepted", candidate: null, staleReasons: [], acceptedReviewState: { status: "current", staleReasons: [] },
      acceptedScript: { revision: 1, candidateJobId: "script-job", contentHash: "script", binding, acceptedAt: "2026-10-11",
        script: { episodes: [{ ep: 1, scenes: [{ sceneId: "S01", characters: [], flow: [{ action: "The light holds." }] }] }] } } },
    storyboardSource: { status: "accepted", candidate: null, staleReasons: [], acceptedReviewState: { status: "current", staleReasons: [] },
      acceptedReview: { revision: 1, candidateJobId: "board-job", contentHash: "board", acceptedAt: "2026-10-11", storyboard: {},
        binding: { ...binding, scriptRevision: 1, scriptContentHash: "script", reviewMinCutSeconds: 2, reviewMaxCutSeconds: 8, reviewMaxSegmentSeconds: 15 } } },
  };
}
